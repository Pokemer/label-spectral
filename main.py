import os
import csv
import numpy as np
import argparse 
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response, RedirectResponse
from pydantic import BaseModel
import spectral.io.envi as envi
from PIL import Image
import io


# ========== 全局配置 ==========
# 默认数据路径和输出路径
DEFAULT_DATA_DIR = "data"
DEFAULT_OUTPUT_DIR = "dataset"

# 解析命令行参数，支持自定义输入/输出目录
parser = argparse.ArgumentParser(description="高光谱数据标注工具")
parser.add_argument("--dir", type=str, default=DEFAULT_DATA_DIR, help="高光谱数据路径")
parser.add_argument("--out", type=str, default=DEFAULT_OUTPUT_DIR, help="结果保存路径")
args, unknown = parser.parse_known_args()

DATA_DIR = args.dir
DATASET_DIR = args.out
os.makedirs(DATASET_DIR, exist_ok=True)  # 确保输出目录存在

print(f"--> 数据目录: {DATA_DIR}")
print(f"--> 结果保存: {DATASET_DIR}")


# ========== FastAPI 应用初始化 ==========
app = FastAPI()
# 挂载静态文件目录（前端页面）
app.mount("/static", StaticFiles(directory="static"), name="static")


# ========== 路由：首页重定向 ==========
@app.get("/")
async def root():
    """根路径重定向到前端主页"""
    return RedirectResponse(url="/static/index.html")


# ========== 数据模型定义 ==========
class LabelData(BaseModel):
    """前端提交的标注数据结构"""
    filename: str          # 文件路径（相对路径）
    x: int                 # 像素横坐标
    y: int                 # 像素纵坐标
    label: str             # 用户输入的类别标签
    spectrum: list         # 光谱向量（浮点数值列表）
    wavelengths: list = [] # 对应的波长列表（可选，用于写入 CSV 表头）


# ========== 高光谱数据加载函数 ==========
def load_hsi_data(relative_path):
    """
    根据相对路径加载 ENVI 格式的高光谱图像（.hdr + .raw）
    """
    # 标准化路径分隔符
    normalized_path = relative_path.replace('/', os.sep).replace('\\', os.sep)
    hdr_path = os.path.join(DATA_DIR, f"{normalized_path}.hdr")
    raw_path = os.path.join(DATA_DIR, f"{normalized_path}.raw")
    
    if not os.path.exists(hdr_path):
        raise FileNotFoundError(f"HDR file not found: {hdr_path}")
        
    try:
        img = envi.open(hdr_path, raw_path)
        return img
    except Exception as e:
        print(f"读取ENVI文件出错: {e}")
        raise e


# ========== API: 获取高光谱文件列表 ==========
@app.get("/api/files")
def get_files():
    """
    递归扫描 DATA_DIR，返回所有 .hdr 文件（作为高光谱数据集索引）
    返回相对路径列表（使用 / 分隔，便于前端使用）
    """
    if not os.path.exists(DATA_DIR):
        return {"files": [], "error": "Path not found"}
    
    file_list = []
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith('.hdr'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, DATA_DIR)
                clean_name = os.path.splitext(rel_path)[0].replace('\\', '/')
                file_list.append(clean_name)
    
    file_list.sort()
    return {"files": file_list}


# ========== API: 获取 RGB 预览图 ==========
@app.get("/api/image")
def get_preview_image(filepath: str):
    """
    生成伪彩色 RGB 预览图：选取近红外、可见光、蓝光波段合成
    使用 2%~98% 百分位进行对比度拉伸，并返回 JPEG 图像
    """
    try:
        img_obj = load_hsi_data(filepath)
        bands = img_obj.shape[2]  # 波段数
        
        # 选择代表性波段（经验值）
        r = img_obj[:, :, int(bands * 0.6)]
        g = img_obj[:, :, int(bands * 0.4)]
        b = img_obj[:, :, int(bands * 0.1)]
        rgb = np.dstack((r, g, b))
        
        # 对比度拉伸（去除异常值影响）
        vmin, vmax = np.percentile(rgb, (2, 98))
        rgb = np.clip((rgb - vmin) / (vmax - vmin) * 255, 0, 255).astype(np.uint8)
        
        # 转为 PIL 并序列化为 JPEG
        pil_img = Image.fromarray(rgb)
        img_byte_arr = io.BytesIO()
        pil_img.save(img_byte_arr, format='JPEG')
        return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== API: 获取指定像素的光谱 ==========
@app.get("/api/spectrum")
def get_spectrum(filepath: str, x: int, y: int):
    """
    返回 (x, y) 位置的光谱向量及对应的波长信息
    波长从 ENVI 元数据中读取；若缺失则使用索引代替
    """
    try:
        img_obj = load_hsi_data(filepath)
        spectrum = img_obj[y, x, :].flatten().tolist()
        wavelengths = img_obj.metadata.get('wavelength', [])
        
        if wavelengths:
            wavelengths = [float(w) for w in wavelengths]
        else:
            wavelengths = list(range(len(spectrum)))
            
        return {"wavelengths": wavelengths, "spectrum": spectrum}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== API: 保存标注结果 ==========
@app.post("/api/save")
def save_label(data: LabelData):
    """
    将用户标注结果追加写入 CSV 文件
    - 首次写入时，根据传回的 wavelengths 生成带物理意义的表头
    - 若无波长信息，则使用 generic 的 band_0, band_1, ... 作为列名
    """
    csv_file = os.path.join(DATASET_DIR, "labeled_data.csv")
    file_exists = os.path.isfile(csv_file)
    
    try:
        with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 首次写入：写入带意义的表头
            if not file_exists:
                if data.wavelengths and len(data.wavelengths) == len(data.spectrum):
                    # 使用波长值作为列名（保留原始精度，转为字符串）
                    band_headers = [str(w) for w in data.wavelengths]
                else:
                    # 回退方案：使用通用波段名
                    band_headers = [f"band_{i}" for i in range(len(data.spectrum))]
                
                header = ["filename", "x", "y", "label"] + band_headers
                writer.writerow(header)
            
            # 写入标注数据行
            row = [data.filename, data.x, data.y, data.label] + data.spectrum
            writer.writerow(row)
            
        return {"status": "success", "message": f"Saved {data.label}"}
    
    except Exception as e:
        print(f"保存失败: {e}")
        raise HTTPException(status_code=500, detail="Save failed")


# ========== 启动入口 ==========
if __name__ == "__main__":
    import uvicorn
    # 启动 FastAPI 服务，监听所有接口（便于 Docker/远程访问）
    uvicorn.run(app, host="0.0.0.0", port=8000)
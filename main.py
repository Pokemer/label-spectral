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

# --- 1. 参数解析 ---
DEFAULT_DATA_DIR = "data"
DEFAULT_OUTPUT_DIR = "dataset"

parser = argparse.ArgumentParser(description="高光谱数据标注工具")
parser.add_argument("--dir", type=str, default=DEFAULT_DATA_DIR, help="高光谱数据路径")
parser.add_argument("--out", type=str, default=DEFAULT_OUTPUT_DIR, help="结果保存路径")

args, unknown = parser.parse_known_args()
DATA_DIR = args.dir
DATASET_DIR = args.out
os.makedirs(DATASET_DIR, exist_ok=True)

print(f"--> 数据目录: {DATA_DIR}")
print(f"--> 结果保存: {DATASET_DIR}")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

# --- 2. 数据模型修正：增加 wavelengths 字段 ---
class LabelData(BaseModel):
    filename: str
    x: int
    y: int
    label: str
    spectrum: list
    wavelengths: list = [] # <--- 关键：允许前端把波长传回来

def load_hsi_data(relative_path):
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

@app.get("/api/files")
def get_files():
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

@app.get("/api/image")
def get_preview_image(filepath: str):
    try:
        img_obj = load_hsi_data(filepath)
        bands = img_obj.shape[2]
        r = img_obj[:, :, int(bands * 0.6)]
        g = img_obj[:, :, int(bands * 0.4)]
        b = img_obj[:, :, int(bands * 0.1)]
        rgb = np.dstack((r, g, b))
        vmin, vmax = np.percentile(rgb, (2, 98))
        rgb = np.clip((rgb - vmin) / (vmax - vmin) * 255, 0, 255).astype(np.uint8)
        pil_img = Image.fromarray(rgb)
        img_byte_arr = io.BytesIO()
        pil_img.save(img_byte_arr, format='JPEG')
        return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spectrum")
def get_spectrum(filepath: str, x: int, y: int):
    try:
        img_obj = load_hsi_data(filepath)
        spectrum = img_obj[y, x, :].flatten().tolist()
        wavelengths = img_obj.metadata.get('wavelength', [])
        wavelengths = [float(w) for w in wavelengths] if wavelengths else list(range(len(spectrum)))
        return {"wavelengths": wavelengths, "spectrum": spectrum}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. 保存逻辑修正：使用传回来的波长写表头 ---
@app.post("/api/save")
def save_label(data: LabelData):
    csv_file = os.path.join(DATASET_DIR, "labeled_data.csv")
    file_exists = os.path.isfile(csv_file)
    
    try:
        with open(csv_file, mode='a', newline='') as f:
            writer = csv.writer(f)
            # 如果是新文件，写表头
            if not file_exists:
                # 优先检查有没有传回波长数据
                if data.wavelengths and len(data.wavelengths) == len(data.spectrum):
                    # 用波长做表头，保留2位小数转字符串
                    band_headers = [str(w) for w in data.wavelengths]
                else:
                    # 回退方案
                    band_headers = [f"band_{i}" for i in range(len(data.spectrum))]
                
                header = ["filename", "x", "y", "label"] + band_headers
                writer.writerow(header)
            
            # 写数据
            row = [data.filename, data.x, data.y, data.label] + data.spectrum
            writer.writerow(row)
            
        return {"status": "success", "message": f"Saved {data.label}"}
    except Exception as e:
        print(f"保存失败: {e}")
        raise HTTPException(status_code=500, detail="Save failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# HSI Label Tool (高光谱数据标注工具)

这是一个用于查看 `.hdr/.raw` 格式高光谱数据，并手动选取像素点制作光谱数据集（CSV 格式）的轻量级工具。

## 1\. 准备工作：安装环境 (必须)

我们需要安装一个叫 **uv** 的工具，它能自动帮你把 Python 环境配好，非常简单。

### 安装 uv

1.  按键盘上的 `Win` 键，输入 `PowerShell`。
2.  在 "Windows PowerShell" 上点击右键，选择 **“以管理员身份运行”**。
3.  复制下面这行代码，粘贴到蓝色窗口中，按回车：
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
4.  安装完成后，**关闭该窗口**。

---

## 2\. 获取软件代码

你可以选择以下任意一种方法下载代码。

### 方法一：直接下载压缩包 (推荐，无需安装 Git)

1.  点击这个链接打开项目主页：[https://github.com/Pokemer/label-spectral](https://www.google.com/search?q=https://github.com/Pokemer/label-spectral)
2.  点击页面右上角的绿色按钮 **Code**，然后选择 **Download ZIP**。
3.  下载完成后，**解压**这个压缩包。
4.  进入解压后的文件夹（通常叫 `label-spectral-main`），确保你能看到 `main.py` 文件。
5.  在文件夹的空白处，**按住 `Shift` 键 + 点击鼠标右键**，选择 **“在此处打开 PowerShell 窗口”**。

### 方法二：使用 Git 克隆 (如果你电脑上有 Git)

1.  在你想存放的文件夹空白处，Shift+右键打开 PowerShell。
2.  输入命令：
    ```bash
    git clone https://github.com/Pokemer/label-spectral.git
    ```
3.  进入文件夹：
    ```bash
    cd label-spectral
    ```

---

## 3\. 初始化环境

**无论你用哪种方法下载，都需要在刚才打开的 PowerShell 窗口中运行一次初始化。**

输入以下命令并回车：

```bash
uv sync
```

_等待进度条跑完，显示 "Resolved..." 或 "Audited..." 即表示成功。软件会自动安装所需的 Python 库。_

---

## 4\. 如何使用

**每次需要使用软件时，请执行以下步骤：**

### 第一步：启动软件

假设你的高光谱数据存放在 **移动硬盘（比如 D 盘）** 的 `D:\数据\2025实验数据` 文件夹里。

在项目文件夹内打开 PowerShell（Shift+右键），输入：

```bash
uv run main.py --dir "D:\数据\2025实验数据"
```

> **注意：**
>
> - `--dir` 后面跟的是存放 `.hdr` 和 `.raw` 文件的**根目录**，软件会自动扫描子文件夹。
> - 如果路径里包含空格，请务必用英文双引号包起来，例如 `"D:\My Data"`。

当看到屏幕显示 `Uvicorn running on http://0.0.0.0:8000` 时，说明启动成功。

### 第二步：网页操作

1.  打开浏览器（推荐 Chrome 或 Edge）。
2.  访问地址：`http://127.0.0.1:8000`
3.  **开始标注**：
    - **左侧列表**：点击文件名，加载高光谱图像。
    - **中间图像**：点击你感兴趣的物体（如水体、餐盒、瓶子等）。
    - **右侧面板**：观察光谱曲线，输入“物体类别”（如 `pp`），点击 **“保存至数据集”**。

---

## 5\. 数据结果

标注好的数据会自动保存在项目文件夹下的 `dataset` 目录中，文件名为 `labeled_data.csv`。

该文件包含了文件名、坐标、标签以及对应的**全波段光谱数据**（第一行表头为真实的波长）。

---

## 常见问题 (FAQ)

- **Q: 运行 `uv` 提示“无法识别为命令”？**
  - A: 说明安装 `uv` 后没有重启终端。请关闭所有 PowerShell 窗口，重新打开再试。
- **Q: 运行 `uv sync` 报错？**
  - A: 请检查你是否在项目文件夹内部打开的终端（你需要能看到 `pyproject.toml` 或 `main.py` 文件）。
- **Q: 怎么退出软件？**
  - A: 在黑色的运行窗口中，按 `Ctrl + C` 即可停止。

---

### 提示

如果你通过 ZIP 下载，文件夹名字可能会带一个 `-main` 后缀（如 `label-spectral-main`），这是正常的，直接进入该文件夹操作即可。

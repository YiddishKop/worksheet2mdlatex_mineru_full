from pathlib import Path
from typing import List, Tuple
import cv2, numpy as np

def preprocess(img):
    """预处理：去噪 + 自适应阈值，生成二值图以利于版面分析。"""
    gray=cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray=cv2.fastNlMeansDenoising(gray, h=10)
    bw=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,35,10)
    return bw

def find_question_boxes(bw)->List[Tuple[int,int,int,int]]:
    """在二值图上寻找疑似题块的外接矩形框。

    - 形态学膨胀后找外轮廓；
    - 过滤小区域噪声（以图像面积比例设下限）；
    - 返回按 (y, x) 排序的矩形列表 (x, y, w, h)。
    """
    k=cv2.getStructuringElement(cv2.MORPH_RECT,(5,2)); dil=cv2.dilate(255-bw,k,1)
    cnts,_=cv2.findContours(dil,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    H,W=bw.shape[:2]; min_area=max(2500,(H*W)//500); boxes=[]
    for c in cnts:
        x,y,w,h=cv2.boundingRect(c)
        if w*h<min_area: continue
        boxes.append((x,y,w,h))
    merged=sorted(boxes,key=lambda b:(b[1],b[0]))
    return merged

def cut_questions(page_path: Path, out_dir: Path) -> List[Path]:
    """对整页图像进行题块切割，并将各题保存为图片。

    - 若未能检测到题块，则直接将整页当作一题保存；
    - 输出文件名格式：`<stem>_q{i}.png`；
    - 返回所有切割后图片的路径列表。
    """
    img=cv2.imread(str(page_path)); bw=preprocess(img); boxes=find_question_boxes(bw)
    if not boxes:
        out=out_dir/f"{page_path.stem}_q1.png"; cv2.imwrite(str(out),img); return [out]
    outs=[]
    for i,(x,y,w,h) in enumerate(boxes,1):
        crop=img[y:y+h,x:x+w]
        p=out_dir/f"{page_path.stem}_q{i}.png"; cv2.imwrite(str(p),crop); outs.append(p)
    return outs

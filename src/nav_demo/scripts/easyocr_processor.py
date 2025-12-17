#!/usr/bin/env python3 
# coding=utf-8 
import os 
import sys 
import easyocr 
import cv2 
import numpy as np 
 
def main(image_path):
    # 设置模型路径 
    model_dir = "/home/ubuuntu2004/planzzz_ws/src/nav_demo/scripts/models" 
    
    # 初始化EasyOCR阅读器（使用本地模型）
    reader = easyocr.Reader(
        lang_list=['ch_sim', 'en'], 
        gpu=False,
        model_storage_directory=model_dir,
        download_enabled=False,  # 禁用自动下载
        detector='craft_mlt_25k',  # 指定检测模型
        recognizer='zh_sim_g2'     # 指定识别模型
    )
    
    # 读取图像 
    img = cv2.imread(image_path)   
    if img is None:
        print(f"❌ 无法读取图像: {image_path}")
        return 
    
    # 执行OCR识别 
    results = reader.readtext(img)   
    
    # 打印识别结果 
    print("🔍 EasyOCR识别结果:")
    for i, (bbox, text, confidence) in enumerate(results):
        print(f"结果 {i+1}: 文本: '{text}' | 置信度: {confidence:.2f}")
    
    # 保存带标注的图像 
    output_path = os.path.splitext(image_path)[0]  + "_ocr.jpg"   
    for bbox, text, confidence in results:
        top_left = tuple(map(int, bbox[0]))
        bottom_right = tuple(map(int, bbox[2]))
        cv2.rectangle(img,  top_left, bottom_right, (0, 255, 0), 2)
        text_position = (top_left[0], top_left[1] - 10)
        cv2.putText(img,  text, text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    cv2.imwrite(output_path,  img)
    print(f"💾 带标注的图像已保存至: {output_path}")
 
if __name__ == "__main__":
    if len(sys.argv)  != 2:
        print("用法: python easyocr_processor.py  <图片路径>")
        sys.exit(1)   
    main(sys.argv[1])   

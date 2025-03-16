import os
import sys
import logging
import re
from typing import List, Dict, Any, Union, Tuple, Dict, Optional, Callable
import cv2
import numpy as np

from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer
from PyQt5.QtGui import QMovie, QPixmap, QPainter, QImage

logger = logging.getLogger(__name__)


class TachieManager:
    """管理角色立绘资源的类"""
    def __init__(self, base_dir="images/apeiria", base_image_name="CH01_01_00", image_size=(300, 500)):
        """初始化TachieManager"""
        self.base_dir = base_dir
        self.base_image_name = base_image_name
        self.image_size = image_size # (width, height)
        self.current_base = "normal"  # 默认基础姿势
        self.current_emotion = "普通"      # 默认表情
        self.available_bases = []         # 可用的基础姿势
        self.available_emotions = {}      # 每个基础姿势可用的表情
        
        # 扫描并加载可用的资源
        self._scan_resources()
        
    def _scan_resources(self):
        """扫描目录中的所有可用资源"""
        if not os.path.exists(self.base_dir):
            print(f"警告: 资源目录 {self.base_dir} 不存在")
            return
            
        files = os.listdir(self.base_dir)
        
        # 找出所有基础姿势, CH01_01_00+(normal|positive|negative).png
        # base_files = [file for file in files if "+" in file]
        pattern = rf"{self.base_image_name}+.*.png"
        base_files = [file for file in files if re.match(pattern, file)]
        for file in base_files:
            base_name = file.split(".")[0].split("+")[-1]
            if base_name not in self.available_bases:
                self.available_bases.append(base_name)
                
        # 找出所有表情差分
        for base in self.available_bases:
            # all files that start with base name and "_{emotion}.png"
            # base_prefix = base.rsplit("_", 1)[0]  
            # emotion_files = [f for f in files if f.startswith(f"{base_prefix}_") and "_" in f.split("_", 2)[2]]
            # 找出所有基础姿势, CH01_01_00_(害羞|高兴).png
            pattern = rf"{self.base_image_name}_.*.png"
            emotion_files = [file for file in files if re.match(pattern, file)]

            emotions = []
            for file in emotion_files:
                emotion = file.split(self.base_image_name + "_")[1].split(".")[0]
                emotions.append(emotion)
            
            self.available_emotions[base] = emotions
            
        print(f"已加载 {len(self.available_bases)} 个基础姿势, {len(self.available_emotions)} 个表情")
        
    def get_base_image_path(self, base_name=None):
        """获取基础姿势图像的路径"""
        if base_name is None:
            base_name = self.current_base

        base_name = f"{self.base_image_name}+{base_name}"
            
        return os.path.join(self.base_dir, f"{base_name}.png")
    
    def get_emotion_image_path(self, emotion=None):
        """获取表情差分图像的路径"""
        if emotion is None:
            emotion = self.current_emotion

        emotion_name = f"{self.base_image_name}_{emotion}"
        return os.path.join(self.base_dir, f"{emotion_name}.png")
    
    def set_base(self, base_name):
        """设置当前基础姿势"""
        logger.info(f"设置基础姿势为 {base_name}")
        if base_name in self.available_bases:
            self.current_base = base_name
            return True
        return False
    
    def set_emotion(self, emotion):
        """设置当前表情"""
        if emotion in self.available_emotions.get(self.current_base, []):
            logger.info(f"设置表情为 {emotion}")
            self.current_emotion = emotion
            return True
        return False
    
    def get_scaled_image(self, pixmap, width=None, height=None):
        """缩放图像，先移除透明区域再缩放"""
        if width is None:
            width = self.image_size[0]
        if height is None:
            height = self.image_size[1]
        
        # 将QPixmap转换为OpenCV格式
        qimg = pixmap.toImage()
        
        # 获取图像尺寸和格式
        img_width = qimg.width()
        img_height = qimg.height()
        
        # 创建numpy数组来存储图像数据
        ptr = qimg.constBits()
        ptr.setsize(qimg.byteCount())
        arr = np.array(ptr).reshape(img_height, img_width, 4)
        
        # 提取alpha通道
        alpha = arr[:, :, 3]
        
        # 找到非透明区域
        non_transparent = alpha > 0
        
        # 如果图像完全透明，返回原始缩放
        if not np.any(non_transparent):
            return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 找到非透明区域的边界
        rows = np.any(non_transparent, axis=1)
        cols = np.any(non_transparent, axis=0)
        
        # 获取非零区域的索引
        y_indices = np.where(rows)[0]
        x_indices = np.where(cols)[0]
        
        # 确保有非透明像素
        if len(y_indices) == 0 or len(x_indices) == 0:
            return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        y_min, y_max = y_indices[[0, -1]]
        x_min, x_max = x_indices[[0, -1]]
        
        # 裁剪原始QImage
        cropped_qimg = qimg.copy(x_min, y_min, x_max - x_min + 1, y_max - y_min + 1)
        
        # 转换回QPixmap
        cropped_pixmap = QPixmap.fromImage(cropped_qimg)
        
        # 缩放裁剪后的图像
        return cropped_pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    def get_composite_image(self):
        """生成组合图像（基础姿势+表情差分）"""
        base_path = self.get_base_image_path()
        emotion_path = self.get_emotion_image_path()
        
        # 加载基础图像
        base_pixmap = QPixmap(base_path)
        if base_pixmap.isNull():
            logger.warning(f"错误: 无法加载基础图像 {base_path}")
            return QPixmap(*self.image_size)  # 返回空白图像
            
        # 检查表情图像是否存在
        if not os.path.exists(emotion_path):
            logger.warning(f"警告: 表情图像不存在 {emotion_path}，仅使用基础图像")
            return self.get_scaled_image(base_pixmap)
            
        # 加载表情图像
        emotion_pixmap = QPixmap(emotion_path)
        if emotion_pixmap.isNull():
            logger.warning(f"错误: 无法加载表情图像 {emotion_path}")
            return self.get_scaled_image(base_pixmap)

            
        # 创建组合图像
        result = QPixmap(base_pixmap.size())
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
        painter.drawPixmap(0, 0, base_pixmap)
        painter.drawPixmap(0, 0, emotion_pixmap)
        painter.end()

        return self.get_scaled_image(result)
    
    def get_head_image(self, head_location: float = 0.3):
        """获取角色头部图像, head_location为头部下端位置比例"""
        composite_image = self.get_composite_image()

        # crop head
        head_height = int(composite_image.height() * head_location)
        head_pixmap = composite_image.copy(0, 0, composite_image.width(), head_height)

        return head_pixmap

    
    def get_available_bases(self):
        """获取所有可用的基础姿势"""
        return self.available_bases
    
    def get_available_emotions(self, base_name=None):
        """获取指定基础姿势的所有可用表情"""
        if base_name is None:
            base_name = self.current_base
        return self.available_emotions.get(base_name, [])
    
    def get_positive_base(self):
        """获取positive姿势"""
        for base in self.available_bases:
            if "positive" in base.lower():
                return base
        return self.current_base
    
    def get_negative_base(self):
        """获取negative姿势"""
        for base in self.available_bases:
            if "negative" in base.lower():
                return base
        return self.current_base
    
    def base_emotion_combinations(self):
        """返回一些特定的姿势和表情组合"""
        return {}
    
    def set_base_emotion_combination(self, combination_name):
        """设置特定的姿势和表情组合"""
        combinations = self.base_emotion_combinations()
        if combination_name in combinations:
            base, emotion = combinations[combination_name]
            self.set_base(base)
            self.set_emotion(emotion)
            return True
        
        logger.warning(f"未找到姿势和表情组合 {combination_name}")
        return False
    
class ApeiriaTachieManager(TachieManager):
    """Apeiria角色立绘资源管理类, 记录一些特定的姿势和表情组合"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def base_emotion_combinations(self):
        """返回一些特定的姿势和表情组合"""
        return {
            "豆豆眼拒绝": ("negative", "ジト目"),
            "普通": ("normal", "普通"),
            "脸红": ("positive", "脸红"),
        }
    

TACHIE_MANAGER_CLSMAP: Dict[str, Callable[..., TachieManager]] = {
    "base": TachieManager,
    "apeiria": ApeiriaTachieManager,
}


    
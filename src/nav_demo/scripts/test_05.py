#!/usr/bin/env python3 
# coding=utf-8 
 
import rospy 
from std_msgs.msg  import String 
from sensor_msgs.msg  import Image 
from cv_bridge import CvBridge, CvBridgeError 
import queue 
import cv2 
import os 
import time 
import threading 
import subprocess 
 
class WaypointNavigator:
    def __init__(self):
        self.target_point  = queue.Queue()
        self.current_point  = None 
        self.wait_timer  = None 
        
        # 图像处理相关变量 
        self.bridge  = CvBridge()  # ROS图像转换工具 
        self.latest_image  = None  # 存储最新图像 
        self.image_ready  = False  # 图像接收状态标志 
        self.image_lock  = threading.Lock()  # 图像访问锁 
        
        # 配置需要拍照的航点 
        self.photo_waypoints  = {"2", "3", "7"}  # 只需在2,3,7航点拍照 
        
        # YOLOv5配置参数 
        self.yolo_script  = "/home/ubuuntu2004/beifeng1/yolov5/yolov5/detect.py"   
        self.yolo_output_dir  = "/home/ubuuntu2004/planzzz_ws/waypoint_images"
        self.yolo_env  = "conda activate yolov5"  # 使用的conda环境 
        
        # EasyOCR配置参数
        self.easyocr_script  = "/home/ubuuntu2004/easyocr/src/scripts/detect_3.py" 
        self.easyocr_output_dir  = "/home/ubuuntu2004/easyocr/src/images"
        self.easyocr_env  = "conda activate easyocr"  # EasyOCR的conda环境
        
        # 确保EasyOCR输出目录存在 
        os.makedirs(self.easyocr_output_dir,  exist_ok=True)
        
        # ROS节点初始化 
        rospy.init_node("wp_node")     
        
        # 创建发布器和订阅器 
        self.navi_pub  = rospy.Publisher("/waterplus/navi_waypoint", String, queue_size=10)
        
        # 订阅导航结果和相机图像 
        rospy.Subscriber("/waterplus/navi_result", String, self.nav_result_callback)     
        rospy.Subscriber("/camera/image_raw", Image, self.image_callback)     
        
        rospy.sleep(1)       # 确保连接建立 
        rospy.loginfo("🚀      航点导航系统初始化完成，等待指令...")
    
    def image_callback(self, msg):
        """相机图像回调函数 - 持续接收最新图像（线程安全）"""
        try:
            # 将ROS图像消息转换为OpenCV格式 
            cv_image = self.bridge.imgmsg_to_cv2(msg,  "bgr8")
            
            # 使用锁确保线程安全 
            with self.image_lock:    
                self.latest_image  = cv_image 
                self.image_ready  = True 
        except CvBridgeError as e:
            rospy.logerr("❌      图像转换错误: %s", e)
    
    def save_current_image(self, waypoint):
        """保存当前航点图像并根据航点触发不同的处理"""
        if not self.image_ready:     
            rospy.logwarn("⚠️      未接收到图像，无法保存")
            return False 
        
        try:
            # 获取当前时间戳
            timestamp = time.strftime("%Y%m%d_%H%M%S") 
            filename = f"waypoint_{waypoint}_{timestamp}.jpg"
            
            # 使用锁确保线程安全 
            with self.image_lock:    
                # 航点2和3保存到YOLO目录 
                if waypoint in {"2", "3"}:
                    os.makedirs(self.yolo_output_dir,  exist_ok=True)
                    filepath = os.path.join(self.yolo_output_dir,  filename)
                    cv2.imwrite(filepath,  self.latest_image) 
                    rospy.loginfo("📸      已保存航点 %s 图像(YOLO): %s", waypoint, filepath)
                
                # 航点7保存到EasyOCR目录 
                if waypoint == "7":
                    filepath = os.path.join(self.easyocr_output_dir,  filename)
                    cv2.imwrite(filepath,  self.latest_image) 
                    rospy.loginfo("📸      已保存航点 %s 图像(EasyOCR): %s", waypoint, filepath)
            
            # 触发相应的处理
            if waypoint in {"2", "3"}:
                rospy.loginfo("⚙️     检测到航点 %s，启动YOLOv5处理...", waypoint)
                self.process_image_with_yolov5(filepath,  waypoint)
            elif waypoint == "7":
                rospy.loginfo("🔍     检测到航点 %s，启动EasyOCR处理...", waypoint)
                self.process_image_with_easyocr(filepath) 
            
            return True 
        except Exception as e:
            rospy.logerr("❌      图像保存失败: %s", e)
            return False 
    
    def process_image_with_yolov5(self, image_path, waypoint):
        """调用YOLOv5模型处理图像"""
        def run_yolo():
            try:
                rospy.loginfo("🚀     启动YOLOv5处理: %s", image_path)
                
                # 构建conda命令 
                conda_cmd = f"source ~/anaconda3/etc/profile.d/conda.sh  && {self.yolo_env}  && "
                
                # 构建YOLOv5命令 
                yolo_cmd = [
                    "python", self.yolo_script,   
                    "--source", image_path,
                    "--project", self.yolo_output_dir,   
                    "--name", f"processed_{waypoint}",
                    "--save-txt", "--save-conf"
                ]
                
                # 完整命令 
                full_cmd = conda_cmd + " ".join(yolo_cmd)
                
                # 执行命令并实时输出结果 
                rospy.loginfo("🔧     执行命令: %s", full_cmd)
                process = subprocess.Popen(
                    full_cmd, 
                    shell=True, 
                    executable="/bin/bash",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # 将stderr合并到stdout 
                    text=True 
                )
                
                # 实时打印输出到当前终端 
                rospy.loginfo("📡      YOLOv5检测结果:")
                while True:
                    output = process.stdout.readline()  
                    if output == '' and process.poll()  is not None:
                        break 
                    if output:
                        # 直接打印到终端（带ROS时间戳）
                        rospy.loginfo(output.strip())  
                
                # 检查结果 
                return_code = process.poll()  
                if return_code == 0:
                    rospy.loginfo("✅     YOLOv5处理成功!")
                    
                    # 获取最新处理结果路径 
                    output_path = os.path.join(   
                        self.yolo_output_dir,   
                        f"processed_{waypoint}",
                        os.path.basename(image_path)   
                    )
                    rospy.loginfo("🖼️     处理结果已保存至: %s", output_path)
                else:
                    rospy.logerr("❌     YOLOv5处理失败! 错误代码: %d", return_code) 
            
            except Exception as e:
                rospy.logerr("❌     YOLOv5处理异常: %s", str(e))
        
        # 在新线程中运行YOLOv5处理
        threading.Thread(target=run_yolo).start()
    
    def process_image_with_easyocr(self, image_path):
        """调用EasyOCR模型处理航点7的图像"""
        def run_easyocr():
            try:
                rospy.loginfo("🚀     启动EasyOCR处理: %s", image_path)
                
                # 构建conda命令 
                conda_cmd = f"source ~/anaconda3/etc/profile.d/conda.sh  && {self.easyocr_env}  && "
                
                # 构建EasyOCR命令 
                easyocr_cmd = [
                    "python", self.easyocr_script, 
                    "--image", image_path 
                ]
                
                # 完整命令 
                full_cmd = conda_cmd + " ".join(easyocr_cmd)
                
                # 执行命令并实时输出结果
                rospy.loginfo("🔧     执行命令: %s", full_cmd)
                process = subprocess.Popen(
                    full_cmd, 
                    shell=True, 
                    executable="/bin/bash",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # 将stderr合并到stdout 
                    text=True 
                )
                
                # 实时打印输出到当前终端 
                rospy.loginfo("🔍      EasyOCR识别结果:")
                while True:
                    output = process.stdout.readline()  
                    if output == '' and process.poll()  is not None:
                        break 
                    if output:
                        # 直接打印到终端（带ROS时间戳）
                        rospy.loginfo(output.strip())  
                
                # 检查结果 
                return_code = process.poll()  
                if return_code == 0:
                    rospy.loginfo("✅     EasyOCR处理成功!")
                else:
                    rospy.logerr("❌     EasyOCR处理失败! 错误代码: %d", return_code) 
            
            except Exception as e:
                rospy.logerr("❌     EasyOCR处理异常: %s", str(e))
        
        # 在新线程中运行EasyOCR处理
        threading.Thread(target=run_easyocr).start()
    
    def nav_result_callback(self, msg):
        """增强型导航结果处理"""
        rospy.logwarn("      原始导航结果 = %s", msg.data)     
        
        # 智能状态识别系统（兼容多种消息格式）
        status = msg.data.lower().strip()     
        success_codes = ["reached", "arrived", "done", "success", "ok"]
        
        if any(code in status for code in success_codes):
            rospy.loginfo("✅      确认到达航点 %s，停留1秒...", self.current_point)     
            
            # 只在指定航点拍照 
            if self.current_point  in self.photo_waypoints:    
                rospy.loginfo("📸      航点 %s 需要拍照，正在保存图像...", self.current_point)    
                self.save_current_image(self.current_point)    
            else:
                rospy.loginfo("⏩      航点 %s 无需拍照，等待1秒后继续...", self.current_point)    
            
            # 创建单次定时器（1秒后触发）
            if self.wait_timer:     
                self.wait_timer.shutdown()       # 防止定时器堆积 
            self.wait_timer  = rospy.Timer(
                rospy.Duration(1),
                self.timer_callback,     
                oneshot=True 
            )
        else:
            rospy.logwarn("⚠️      未识别状态: %s", msg.data)     
    
    def timer_callback(self, event):
        """安全航点切换系统"""
        rospy.loginfo("⌛      停留结束，准备下一航点...")
        if not self.target_point.empty():     
            # 获取并发布下个航点 
            self.current_point  = self.target_point.get()     
            navi_msg = String()
            navi_msg.data  = self.current_point      
            self.navi_pub.publish(navi_msg)     
            rospy.loginfo("🚀      发布新航点: %s", self.current_point)     
        else:
            rospy.loginfo("🎉      所有航点已完成!")
            self.wait_timer  = None 
    
    def start_navigation(self, waypoints):
        """启动导航流程"""
        # 清空可能存在的旧队列 
        while not self.target_point.empty():     
            self.target_point.get()     
        
        # 加载航点队列 
        for point in waypoints:
            self.target_point.put(point)     
        
        # 发布初始航点 
        if not self.target_point.empty():     
            self.current_point  = self.target_point.get()     
            navi_msg = String()
            navi_msg.data  = self.current_point     
            self.navi_pub.publish(navi_msg)     
            rospy.loginfo("🚦      启动导航，前往航点: %s", self.current_point)     
 
if __name__ == "__main__":
    rospy.loginfo("===      航点导航系统初始化 ===")
    navigator = WaypointNavigator()
    
    # 设置航点序列 
    waypoints = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    navigator.start_navigation(waypoints)     
    
    # 保持节点运行 
    rospy.spin() 
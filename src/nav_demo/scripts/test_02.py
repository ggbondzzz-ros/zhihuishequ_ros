#!/usr/bin/env python3 
# coding=utf-8 
 
import rospy 
# ROS Python客户端库，用于节点初始化、话题通信、参数服务器交互等核心功能。
 
from std_msgs.msg  import String 
# 标准消息类型，用于传输简单的字符串数据（如状态信息、识别结果等）。
 
from sensor_msgs.msg  import Image 
# 定义图像传感器消息格式，用于接收摄像头发布的原始图像数据（/camera/image_raw）。
 
from cv_bridge import CvBridge, CvBridgeError 
# 用于在ROS的Image消息与OpenCV的Mat格式之间进行转换，实现图像处理桥梁。
 
import queue 
# 提供线程安全的队列结构，可用于缓存图像帧或任务指令，避免数据竞争。
 
import cv2 
# OpenCV库，用于图像处理操作：显示、保存、裁剪、预处理等。
 
import os 
# 操作系统接口库，用于创建目录、管理文件路径（如保存图片到指定文件夹）。
 
import time 
# 提供时间相关功能，可用于打时间戳、延时控制、性能测试等。
 
import threading 
# 支持多线程编程，便于并发执行图像处理、识别推理等耗时任务，提升响应效率。
 
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
        
        # ROS节点初始化 
        rospy.init_node("wp_node")  
        
        # 创建发布器和订阅器 
        self.navi_pub  = rospy.Publisher("/waterplus/navi_waypoint", String, queue_size=10)
        
        # 订阅导航结果和相机图像 
        rospy.Subscriber("/waterplus/navi_result", String, self.nav_result_callback)  
        rospy.Subscriber("/camera/image_raw", Image, self.image_callback)  
        
        rospy.sleep(1)    # 确保连接建立 
        rospy.loginfo("🚀   航点导航系统初始化完成，等待指令...")
    
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
            rospy.logerr("❌   图像转换错误: %s", e)
    
    def save_current_image(self, waypoint):
        """保存当前航点图像到当前文件夹"""
        if not self.image_ready:  
            rospy.logwarn("⚠️   未接收到图像，无法保存")
            return False 
        
        try:
            # 获取当前工作目录 
            current_dir = os.getcwd()  
            
            # 创建图像保存目录（如果不存在）
            save_dir = os.path.join(current_dir,  "waypoint_images")
            if not os.path.exists(save_dir):  
                os.makedirs(save_dir)  
                rospy.loginfo("📁   创建图像保存目录: %s", save_dir)
            
            # 生成带时间戳的文件名 
            timestamp = time.strftime("%Y%m%d_%H%M%S")  
            filename = f"waypoint_{waypoint}_{timestamp}.jpg"
            filepath = os.path.join(save_dir,  filename)
            
            # 使用锁确保线程安全 
            with self.image_lock: 
                cv2.imwrite(filepath,  self.latest_image)  
            
            rospy.loginfo("📸   已保存航点 %s 图像: %s", waypoint, filename)
            return True 
        except Exception as e:
            rospy.logerr("❌   图像保存失败: %s", e)
            return False 
    
    def nav_result_callback(self, msg):
        """增强型导航结果处理"""
        rospy.logwarn("   原始导航结果 = %s", msg.data)  
        
        # 智能状态识别系统（兼容多种消息格式）
        status = msg.data.lower().strip()  
        success_codes = ["reached", "arrived", "done", "success", "ok"]
        
        if any(code in status for code in success_codes):
            rospy.loginfo("✅   确认到达航点 %s，停留1秒...", self.current_point)  
            
            # 只在指定航点拍照 
            if self.current_point  in self.photo_waypoints: 
                rospy.loginfo("📸   航点 %s 需要拍照，正在保存图像...", self.current_point) 
                self.save_current_image(self.current_point) 
            else:
                rospy.loginfo("⏩   航点 %s 无需拍照，等待1秒后继续...", self.current_point) 
            
            # 创建单次定时器（1秒后触发）
            if self.wait_timer:  
                self.wait_timer.shutdown()    # 防止定时器堆积 
            self.wait_timer  = rospy.Timer(
                rospy.Duration(1),
                self.timer_callback,  
                oneshot=True 
            )
        else:
            rospy.logwarn("⚠️   未识别状态: %s", msg.data)  
    
    def timer_callback(self, event):
        """安全航点切换系统"""
        rospy.loginfo("⌛   停留结束，准备下一航点...")
        if not self.target_point.empty():  
            # 获取并发布下个航点 
            self.current_point  = self.target_point.get()  
            navi_msg = String()
            navi_msg.data  = self.current_point   
            self.navi_pub.publish(navi_msg)  
            rospy.loginfo("🚀   发布新航点: %s", self.current_point)  
        else:
            rospy.loginfo("🎉   所有航点已完成!")
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
            rospy.loginfo("🚦   启动导航，前往航点: %s", self.current_point)  
 
if __name__ == "__main__":
    rospy.loginfo("===   航点导航系统初始化 ===")
    navigator = WaypointNavigator()
    
    # 设置航点序列 
    waypoints = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    navigator.start_navigation(waypoints)  
    
    # 保持节点运行 
    rospy.spin() 
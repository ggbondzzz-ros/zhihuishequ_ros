#!/usr/bin/env python3
# coding=utf-8

import rospy
# ROS核心库：用于初始化节点、管理话题通信、控制程序生命周期。
 
import cv2
# OpenCV库：用于图像处理（如显示、保存、格式转换），支持摄像头实时画面可视化。
 
from sensor_msgs.msg  import Image
# ROS标准图像消息类型：订阅来自摄像头（如/camera/image_raw）的原始图像数据流。
 
from cv_bridge import CvBridge, CvBridgeError
# 桥梁工具：实现ROS图像消息（sensor_msgs/Image）与OpenCV图像（cv::Mat）之间的相互转换。

# 彩色图像回调函数
def Cam_RGB_Callback(msg):
    bridge = CvBridge()
    try:
        cv_image = bridge.imgmsg_to_cv2(msg, "bgr8")
    except CvBridgeError as e:
        rospy.logerr("格式转换错误: %s", e)
        return

    # 弹出窗口显示图片
    cv2.imshow("RGB", cv_image)
    cv2.waitKey(1)

# 主函数
if __name__ == "__main__":
    rospy.init_node("image_node")
    # 订阅机器人视觉传感器图像话题
    rgb_sub = rospy.Subscriber("/camera/image_raw",Image,Cam_RGB_Callback,queue_size=10)
    rospy.spin()

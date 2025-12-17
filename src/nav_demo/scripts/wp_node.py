#!/usr/bin/env python3
# coding=utf-8

import rospy
from std_msgs.msg  import String
import queue

class WaypointNavigator:
    def __init__(self):
        self.target_point  = queue.Queue()
        self.current_point  = None
        self.wait_timer  = None

        # ROS节点初始化
        rospy.init_node("wp_node")

        # 创建发布器和订阅器
        self.navi_pub  = rospy.Publisher("/waterplus/navi_waypoint", String, queue_size=10)
        rospy.Subscriber("/waterplus/navi_result", String, self.nav_result_callback)
        rospy.sleep(1)    # 确保连接建立

    def nav_result_callback(self, msg):
        """增强型导航结果处理"""
        rospy.logwarn(" 原始导航结果 = %s", msg.data)

        # 智能状态识别系统（兼容多种消息格式）
        status = msg.data.lower().strip()
        success_codes = ["reached", "arrived", "done", "success", "ok"]

        if any(code in status for code in success_codes):
            rospy.loginfo("✅  确认到达航点 %s，停留3秒...", self.current_point)

            # 创建单次定时器（3秒后触发）
            if self.wait_timer:
                self.wait_timer.shutdown()   # 防止定时器堆积
            self.wait_timer  = rospy.Timer(rospy.Duration(3), self.timer_callback,  oneshot=True)
        else:
            rospy.logwarn("⚠️  未识别状态: %s", msg.data)

    def timer_callback(self, event):
        """安全航点切换系统"""
        rospy.loginfo("⌛  停留结束，准备下一航点...")
        if not self.target_point.empty():
            # 获取并发布下个航点
            self.current_point  = self.target_point.get()
            navi_msg = String()
            navi_msg.data  = self.current_point
            self.navi_pub.publish(navi_msg)
            rospy.loginfo("🚀  发布新航点: %s", self.current_point)
        else:
            rospy.loginfo("🎉  所有航点已完成!")
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
            rospy.loginfo("🚦  启动导航，前往航点: %s", self.current_point)

if __name__ == "__main__":
    rospy.loginfo("===  航点导航系统初始化 ===")
    navigator = WaypointNavigator()

    # 设置航点序列
    waypoints = ["1", "2", "3", "4", "5", "6"]
    navigator.start_navigation(waypoints)

    # 保持节点运行
    rospy.spin()
import time
import csv
import socket
import json
import math
import rclpy
from rclpy.node import Node
import rclpy.node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from SvayaAPI.CartesianPose import CartesianPose
from SvayaAPI.Frame import Frame
from SvayaAPI.clientApi import SvayaApi
from SvayaAPI.Trajectory import Trajectory
import tkinter as tk
import queue
import numpy as np
from roboticstoolbox import DHRobot, RevoluteMDH
from spatialmath import SE3
import threading
from rclpy.executors import MultiThreadedExecutor
from functools import partial
from std_msgs.msg import Float64
import os
from datetime import datetime

ip = "192.168.20.203" 

def error_callack(error_priority, error_msg, error_status):
    print("Error: ", error_priority, error_msg, error_status)
    if error_priority == "info":
        print("Info: ", error_msg, error_status)
    elif error_priority == "medium":
        print("Medium: ", error_msg, error_status)
    elif error_priority == "high":
        print("High: ", error_msg, error_status) 

class mt_jts_v_q_data(Node):
    def __init__(self, cobot):
        super().__init__('mt_jts_v_q_data')

        self.cobot = cobot
        self.count = 1
        self.max_count = 100
        self.is_logging = False

        self.MotorTorque_data = []
        self.JtsBised_data = []
        self.actual_velocity = []
        self.joint_state = []
        self.get_state_data = []
        
        # ==========================================
        # File Path Setup 
        # ==========================================
        self.folder_path = "/home/pratap-karmakar/srl06_ros_wrapper/Motor_jts_data_logs/EXP_1"
        os.makedirs(self.folder_path, exist_ok=True)  

        # Initialize CSV variables to None
        self.motor_data_csv = None
        self.motor_data_writer = None

        # ==========================================
        # Publisher Creation
        # ==========================================
        self.motor_pub = self.create_publisher(Float64MultiArray, "Motor_Torque_data", 10)
        self.jts_pub = self.create_publisher(Float64MultiArray, "Jts_Biased_data", 10)
        
        self.read_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.read_thread.start()   

    # ==========================================
    # Dynamic CSV Creation
    # ==========================================
    def start_logging(self, joint_num):
        self.timestamp = datetime.now().strftime("%d.%m.%Y_%H:%M:%S")
        self.file_name = f"J_{joint_num}_{self.timestamp}.csv"
        self.file_path = os.path.join(self.folder_path, self.file_name)

        # Open a new file for this specific joint log
        self.motor_data_csv = open(self.file_path, "w", newline="")
        self.motor_data_writer = csv.writer(self.motor_data_csv)

        # Write the header
        self.motor_data_writer.writerow([
            "timestamp", "m_t_1", "m_t_2", "m_t_3", "m_t_4", "m_t_5", "m_t_6",
            "jts1", "jts2", "jts3", "jts4", "jts5", "jts6",
            "v1", "v2", "v3", "v4", "v5", "v6",
            "q1", "q2", "q3", "q4", "q5", "q6"
        ])
        self.is_logging = True

    def stop_logging(self):
        self.is_logging = False
        time.sleep(0.01) # Give timer loop a tiny moment to finish writing
        if self.motor_data_csv is not None:
            self.motor_data_csv.close()
            self.motor_data_csv = None
            self.motor_data_writer = None

    # ==========================================
    # Data Read From Cobot 
    # ==========================================
    def read_data(self):  
        self.MotorTorque_data = self.cobot.getMotorTorqueData() 
        self.JtsBised_data = self.cobot.getJTSBiasedData()  
        self.actual_velocity = self.cobot.getJointVelocities()
        self.joint_state = self.cobot.getJointValues()

    # ==========================================
    # Publish Motor Torque & JTS Biased Data 
    # ==========================================
    def publish_data(self):   
        msg1 = Float64MultiArray() 
        msg1.data = self.MotorTorque_data
        self.motor_pub.publish(msg1)    

        msg2 = Float64MultiArray()
        msg2.data = self.JtsBised_data 
        self.jts_pub.publish(msg2)  

    # ==========================================
    # Fixed Timer Loop (Every 5 ms / 200 Hz)
    # ==========================================
    def timer_loop(self): 
        period = 0.005       
        next_time = time.perf_counter()     

        while rclpy.ok(): 
            next_time += period 
            self.read_data()
            self.publish_data()

            if self.is_logging and self.motor_data_writer is not None:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")     
                current_exp_data = [timestamp] + self.MotorTorque_data + self.JtsBised_data + self.actual_velocity + self.joint_state
                self.motor_data_writer.writerow(current_exp_data)
                    
            # Timing Control  
            now = time.perf_counter()
            sleep_time = next_time - now

            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_time = now  

# ==============================================================================
# USER INPUT LOOP
# ==============================================================================
def user_input(cobot, node): 
    while True:
        time.sleep(0.5)
        
        try:
            task_number = int(input(
                "\n========================================================\n"
                " Which Task Do You Want To Execute? \n"
                "--------------------------------------------------------\n"
                " Press 1 To 6 For Joints 1-6 (Iterates Velocities 30 To 45) \n"
                " Disable -> 7 | Enable -> 8 | Real -> 9 | Auto -> 10 \n"
                " Exit -> 99 \n"
                "========================================================\n"
                "Enter Task Number: "
            ))

        except ValueError: 
            print("\nInvalid Input. Please Enter A Valid Number.")
            continue

        print(f"\nThe Entered Task Number Is: {task_number}\n")

        if task_number == 0:    
            print("Cobot Status: ", cobot.getState())

        elif task_number == 1:   
            print(">>> Moving Joint 1 (Velocities 30 To 45)")
            print(">>> Data Logging Started...")
            node.start_logging(task_number) # Dynamic Logging Start

            vel = 30.0
            acc = 30.0
            while vel <= 46.0:
                print(f"--- Running Joint 1 With Velocity: {vel} ---")
                for i in range(2):
                    q_pos = [ 150.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                    q_neg = [-150.0, 0.0, 0.0, 0.0, 0.0, 0.0]

                    cobot.moveJoints(q_pos, vel, acc)
                    cobot.waitForTime(1)
                    cobot.moveJoints(q_neg, vel, acc)
                    cobot.waitForTime(1)
                    print(f"    Velocity {vel}, Cycle No: {i + 1} Completed...")
                
                vel += 2.0

            node.stop_logging() # Dynamic Logging Stop
            print(">>> Use Dead Man Switch If Robot Is Real...")
            time.sleep(2)
            cobot.goToHome(30.0, 30.0)
            cobot.waitForTime(0.5)
            
        elif task_number == 2:
            print(">>> Moving Joint 2 (Velocities 30 To 45)")
            print(">>> Data Logging Started...")
            node.start_logging(task_number)

            vel = 30.0
            acc = 30.0
            while vel <= 46.0: # Fixed the loop to match behavior from other joints
                print(f"--- Running Joint 2 With Velocity: {vel} ---")
                for i in range(2):
                    q_pos = [0.0,  60.0, 0.0, 0.0, 0.0, 0.0]
                    q_neg = [0.0, -60.0, 0.0, 0.0, 0.0, 0.0]

                    cobot.moveJoints(q_pos, vel, acc)
                    cobot.waitForTime(1)
                    cobot.moveJoints(q_neg, vel, acc)
                    cobot.waitForTime(1)
                    print(f"    Velocity {vel}, Cycle No: {i + 1} Completed...")
                
                vel += 2.0 

            node.stop_logging()
            print(">>> Use Dead Man Switch If Robot Is Real...")
            time.sleep(2)
            cobot.goToHome(30.0, 30.0)
            cobot.waitForTime(0.5)

        elif task_number == 3: 
            print(">>> Moving Joint 3 (Velocities 30 To 45)")
            print(">>> Data Logging Started...")
            node.start_logging(task_number)

            vel = 30.0
            acc = 30.0
            while vel <= 40.0:
                print(f"--- Running Joint 3 With Velocity: {vel} ---")
                for i in range(2):
                    q_pos = [0.0, 0.0,  100.0, 0.0, 0.0, 0.0] 
                    q_neg = [0.0, 0.0, -100.0, 0.0, 0.0, 0.0] 

                    cobot.moveJoints(q_pos, vel, acc)
                    cobot.waitForTime(1)
                    cobot.moveJoints(q_neg, vel, acc)
                    cobot.waitForTime(1)
                    print(f"    Velocity {vel}, Cycle No: {i + 1} Completed...")
                
                vel += 10.0

            node.stop_logging()
            print(">>> Use Dead Man Switch If Robot Is Real...")
            time.sleep(2)
            cobot.goToHome(30.0, 30.0)
            cobot.waitForTime(0.5) 
          
        elif task_number == 4: 
            print(">>> Moving Joint 4 (Velocities 30 To 45)")
            print(">>> Data Logging Started...")
            node.start_logging(task_number)

            vel = 30.0
            acc = 30.0
            while vel <= 46.0:
                print(f"--- Running Joint 4 With Velocity: {vel} ---")
                for i in range(2):
                    q_pos = [0.0, 0.0, 0.0,  120.0, 0.0, 0.0] 
                    q_neg = [0.0, 0.0, 0.0, -120.0, 0.0, 0.0]

                    cobot.moveJoints(q_pos, vel, acc)
                    cobot.waitForTime(1)
                    cobot.moveJoints(q_neg, vel, acc)
                    cobot.waitForTime(1)
                    print(f"    Velocity {vel}, Cycle No: {i + 1} Completed...")
                
                vel += 2.0

            node.stop_logging()
            print(">>> Use Dead Man Switch If Robot Is Real...")
            time.sleep(2)
            cobot.goToHome(30.0, 30.0)
            cobot.waitForTime(0.5) 

        elif task_number == 5: 
            print(">>> Moving Joint 5 (Velocities 30 To 45)")
            print(">>> Data Logging Started...")
            node.start_logging(task_number)

            vel = 30.0
            acc = 30.0
            while vel <= 46.0:
                print(f"--- Running Joint 5 With Velocity: {vel} ---")
                for i in range(2):
                    q_pos = [0.0, 0.0, 0.0, 0.0,  100.0, 0.0] 
                    q_neg = [0.0, 0.0, 0.0, 0.0, -100.0, 0.0] 

                    cobot.moveJoints(q_pos, vel, acc)
                    cobot.waitForTime(1)
                    cobot.moveJoints(q_neg, vel, acc)
                    cobot.waitForTime(1)
                    print(f"    Velocity {vel}, Cycle No: {i + 1} Completed...")
                
                vel += 2.0

            node.stop_logging()
            print(">>> Use Dead Man Switch If Robot Is Real...")
            time.sleep(2)
            cobot.goToHome(30.0, 30.0)
            cobot.waitForTime(0.5) 
 
        elif task_number == 6: 
            print(">>> Moving Joint 6 (Velocities 30 To 45)")
            print(">>> Data Logging Started...")
            node.start_logging(task_number)
            
            vel = 30.0
            acc = 30.0
            while vel <= 46.0:
                print(f"--- Running Joint 6 With Velocity: {vel} ---")
                for i in range(2):
                    q_pos = [0.0, 0.0, 0.0, 0.0, 0.0,  120.0]
                    q_neg = [0.0, 0.0, 0.0, 0.0, 0.0, -120.0]

                    cobot.moveJoints(q_pos, vel, acc)
                    cobot.waitForTime(1)
                    cobot.moveJoints(q_neg, vel, acc)
                    cobot.waitForTime(1)
                    print(f"    Velocity {vel}, Cycle No: {i + 1} Completed...")
                
                vel += 2.0
                
            node.stop_logging()
            print(">>> Use Dead Man Switch If Robot Is Real...")
            time.sleep(2)
            cobot.goToHome(30.0, 30.0)
            cobot.waitForTime(0.5)    
                
        elif task_number == 7:
            print(">>> Disabling Robot...")
            cobot.disableRobot()
            cobot.waitForTime(0.5)

        elif task_number == 8:
            print(">>> Enabling Robot...")
            cobot.enableRobot()
            cobot.waitForTime(0.5)

        elif task_number == 9:
            print(">>> Switching To Real Mode...")
            cobot.switchToReal()
            cobot.waitForTime(0.5)

        elif task_number == 10:
            print(">>> Switching To Auto Mode...")
            cobot.switchToAuto()
            cobot.waitForTime(0.5)

        elif task_number == 99:
            print(">>> Exiting Program And Disabling Robot...")
            cobot.disableRobot()
            break

        else:
            print("\nInvalid Task Entered.")

def main():
    rclpy.init()

    cobot = SvayaApi()
    cobot.initialize(ip, error_callack) 
    print("\n... Robot Initialized Successfully ...\n")
   
    time.sleep(10)
    print("Sleep Time Over...")
    
    # FT bias setup
    cobot.setFTBiasState(True, 1)
    time.sleep(1)
    cobot.setFTBiasState(False, 1)

    # UPDATED NODE INITIALIZATION
    node = mt_jts_v_q_data(cobot)

    # ROS spin thread
    main_ros_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True
    )
    main_ros_thread.start()

    try:
        user_input(cobot, node)

    except KeyboardInterrupt:
        print("\n\033[33m... Aborting Main Program ... \n\nPlease Wait... \033[0m")
        
    finally:
        print("Shutting Down...")
        time.sleep(0.1)
        node.destroy_node()      # destroy ROS node
        rclpy.shutdown()         # shutdown ROS
        cobot.__del__()          # cleanup robot API

if __name__ == "__main__":
    main()
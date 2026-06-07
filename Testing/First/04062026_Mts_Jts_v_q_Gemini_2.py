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

class MotorTorque_and_Jtsbiased_data(Node):

    def __init__(self, cobot):
        super().__init__('MotorTorque_and_Jtsbiased_data')
        self.cobot = cobot
        
        self.MotorTorque_data = []
        self.JtsBised_data = []
        self.actual_velocity = []
        self.joint_state = []
      
        # Logging flags and file variables
        self.is_logging = False
        self.motor_data_csv = None
        self.motor_data_writer = None
        
        self.folder_path = "/home/pratap-karmakar/srl06_ros_wrapper/Motor_jts_data_logs/EXP_1"
        
        # Ensure directory exists immediately
        os.makedirs(self.folder_path, exist_ok=True)  

        # Publishers    
        self.motor_pub = self.create_publisher(Float64MultiArray, "Motor_Torque_data", 10)
        self.jts_pub = self.create_publisher(Float64MultiArray, "Jts_Biased_data", 10)
        
        self.read_thread = threading.Thread(
            target=self.timer_loop,
            daemon=True
        )
        self.read_thread.start()    

    def start_logging(self, task_number):
        if self.is_logging:
            self.stop_logging()
            
        timestamp = datetime.now().strftime("%d.%m.%Y_%H_%M_%S")
        file_name = f"J{task_number}_{timestamp}.csv"
        file_path = os.path.join(self.folder_path, file_name)
        
        # Open file and ensure it writes immediately
        self.motor_data_csv = open(file_path, "a", newline="")
        self.motor_data_writer = csv.writer(self.motor_data_csv)
        
        self.motor_data_writer.writerow([
            "timestamp", "m_t_1", "m_t_2", "m_t_3", "m_t_4", "m_t_5", "m_t_6",
            "jts1", "jts2", "jts3", "jts4", "jts5", "jts6",
            "v1", "v2", "v3", "v4", "v5", "v6",
            "q1", "q2", "q3", "q4", "q5", "q6"
        ])
        
        # Force the OS to create and write the file to the folder immediately
        self.motor_data_csv.flush()
        os.fsync(self.motor_data_csv.fileno())
        
        self.is_logging = True
        print(f"\n---> Started recording continuous data.")
        print(f"---> SAVING TO EXACT PATH: {os.path.abspath(file_path)}")

    def stop_logging(self):
        self.is_logging = False
        if self.motor_data_csv:
            # Final flush and close
            self.motor_data_csv.flush()
            self.motor_data_csv.close()
            self.motor_data_csv = None
        print("---> Stopped recording data.\n")

    def read_data(self):  
        self.MotorTorque_data = self.cobot.getMotorTorqueData() 
        self.JtsBised_data = self.cobot.getJTSBiasedData()  
        self.actual_velocity = self.cobot.getJointVelocities()
        self.joint_state = self.cobot.getJointValues()

    def publish_data(self):   
        msg1 = Float64MultiArray() 
        msg1.data = self.MotorTorque_data if self.MotorTorque_data else []
        self.motor_pub.publish(msg1)    

        msg2 = Float64MultiArray()
        msg2.data = self.JtsBised_data if self.JtsBised_data else []
        self.jts_pub.publish(msg2)  

    def timer_loop(self): 
        period = 0.005       
        next_time = time.perf_counter()     

        while rclpy.ok(): 
            next_time += period 
            
            self.read_data()
            self.publish_data() 

            # Continuously log data at 200Hz IF logging is active
            if self.is_logging and self.motor_data_writer:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]     
                
                mt = self.MotorTorque_data if self.MotorTorque_data else [0]*6
                jt = self.JtsBised_data if self.JtsBised_data else [0]*6
                vel = self.actual_velocity if self.actual_velocity else [0]*6
                j_state = self.joint_state if self.joint_state else [0]*6
                
                current_exp_data = [timestamp] + mt + jt + vel + j_state
                self.motor_data_writer.writerow(current_exp_data)
                
                # Flush every write so it doesn't stay trapped in memory
                self.motor_data_csv.flush()

            # Timing control  
            now = time.perf_counter()
            sleep_time = next_time - now

            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_time = now  

                    
# =========================
# USER INPUT LOOP
# =========================
def user_input(cobot, node): 
    while True:
        time.sleep(0.5)

        try:
            task_number = int(input("Which task you want to Execute?\n Task number 1 - 5 for joint movement\n Press task number 7 -> disable, 8 -> enable, 9 -> real\n> "))
        except ValueError: 
            print("Invalid input")
            continue

        print("The Entered Task Number is:", task_number)

        if task_number == 0:    
            print("cobot status...", cobot.getState())

        elif task_number == 1:   
            print("Move Joint 1")

        elif task_number == 2:
            print("Move Joint 2")

        elif task_number == 3: 
            print("Move Joint 3")
          
        elif task_number == 4: 
            print("Move Joint 4")

        elif task_number == 5: 
            print("Move Joint 5")
       
        elif task_number == 6: 
            print("Move Joint 6")

            # Start recording data continuously
            node.start_logging(task_number)

            for _ in range(3):
                q_1 = [0.0, 0.0, 0.0, 0.0, 0.0, 90.0] 
                q_2 = [0.0, 0.0, 0.0, 0.0, 0.0, -90.0] 

                cobot.moveJoints(q_1, 30.0, 30.0)
                cobot.waitForTime(1)

                cobot.moveJoints(q_2, 30.0, 30.0)
                cobot.waitForTime(1)

            # Stop recording data once the loop is finished
            node.stop_logging()

        elif task_number == 7:
            cobot.disableRobot()
            cobot.waitForTime(0.5)

        elif task_number == 8:
            cobot.enableRobot() 
            cobot.waitForTime(0.5)

        elif task_number == 9:
            cobot.switchToReal()
            cobot.waitForTime(0.5)

        elif task_number == 99:
            cobot.disableRobot()
            break

        else:
            print("Invalid task")


def main():
    rclpy.init()

    cobot = SvayaApi()
    print("\n...Robot initialized successfully...\n")
    print("sleep time over...")

    node = MotorTorque_and_Jtsbiased_data(cobot)

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
        print("\033[33m... Aborting, Main Program ... \n\nPlease Wait... \033[0m")
        node.stop_logging() 
        
    finally:
        print("Shutting down...")
        time.sleep(0.1)
      
        node.destroy_node()      
        rclpy.shutdown()         
        cobot.__del__()          


if __name__ == "__main__":
    main()
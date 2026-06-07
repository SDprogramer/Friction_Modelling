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
        self.count = 1
        self.max_count = 100
        
        # This flag controls CSV writing
        self.is_logging = False 
        
        self.MotorTorque_data = []
        self.JtsBised_data = []
        self.actual_velocity = []
        self.joint_state = []
      
        ## file_path setup and csv initialization 
        self.folder_path = "/home/pratap-karmakar/srl06_ros_wrapper/Motor_jts_data_logs/EXP_1"
        os.makedirs(self.folder_path, exist_ok=True)  

        self.timestamp = datetime.now().strftime("%d.%m.%Y_%H:%M:%S")
        self.file_name = f"{self.timestamp}.csv"
        self.file_path = os.path.join(self.folder_path, self.file_name)
        
        file_exists = os.path.exists(self.file_path)

        self.motor_data_csv = open(self.file_path, "a", newline="")
        self.motor_data_writer = csv.writer(self.motor_data_csv)

        if not file_exists:
            self.motor_data_writer.writerow([
                    "timestamp", "m_t_1", "m_t_2", "m_t_3", "m_t_4", "m_t_5", "m_t_6",
                    "jts1", "jts2", "jts3", "jts4", "jts5", "jts6",
                    "v1", "v2", "v3", "v4", "v5", "v6",
                    "q1", "q2", "q3", "q4", "q5", "q6"
                ])

        ########### publisher creation    
        self.motor_pub = self.create_publisher(Float64MultiArray, "Motor_Torque_data", 10)
        self.jts_pub = self.create_publisher(Float64MultiArray, "Jts_Biased_data", 10)
        
        self.read_thread = threading.Thread(
            target=self.timer_loop,
            daemon=True
        )
        self.read_thread.start()   

    ######### data read from cobot 
    def read_data(self):  
        self.MotorTorque_data = self.cobot.getMotorTorqueData() 
        self.JtsBised_data = self.cobot.getJTSBiasedData()  
        self.actual_velocity = self.cobot.getJointVelocities()
        self.joint_state = self.cobot.getJointValues()

    ########### publish Motor_torque and jts_biased_data 
    def publish_data(self):   
        msg1 = Float64MultiArray() 
        msg1.data = self.MotorTorque_data
        self.motor_pub.publish(msg1)    

        msg2 = Float64MultiArray()
        msg2.data = self.JtsBised_data 
        self.jts_pub.publish(msg2)  

    ######### fixed timer loop call for every 5 ms (200 Hz)
    def timer_loop(self): 
        period = 0.005       
        next_time = time.perf_counter()     

        while rclpy.ok(): 
            next_time += period 
            self.read_data()
            self.publish_data()

            # ONLY log data if the flag is True
            if self.is_logging:
                # High precision timestamp (Hours:Minutes:Seconds.Microseconds)
                timestamp = datetime.now().strftime("%H:%M:%S.%f")     
                            
                current_exp_data = (
                    [timestamp] + 
                    self.MotorTorque_data + 
                    self.JtsBised_data + 
                    self.actual_velocity + 
                    self.joint_state
                )
                
                self.motor_data_writer.writerow(current_exp_data)
                    
            ## timing control  
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
            task_number = int(input("\nWhich task you want to Execute?\n Task number 1 - 5 for joint movement\n Press task number 6 -> automated cycle (w/ Data Logging)\n Press task number 7 -> disable, 8 -> enable, 9 -> real: "))
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
            print("Executing Automated Sequence: 0 -> 90 -> -90 (3 Cycles)")

            # Define absolute joint positions
            q_home = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            q_90 = [0.0, 0.0, 0.0, 0.0, 0.0, 90.0]
            q_minus_90 = [0.0, 0.0, 0.0, 0.0, 0.0, -90.0]

            # >>> START DATA LOGGING <<<
            print(">>> STARTING DATA COLLECTION <<<")
            node.is_logging = True

            for cycle in range(3):
                print(f"--- Cycle {cycle + 1} of 3 ---")
                
                # Move to 0
                cobot.moveJoints(q_home, 30.0, 30.0)
                cobot.waitForTime(1.5) # Wait sufficient time for motion to settle

                # Move to 90
                cobot.moveJoints(q_90, 30.0, 30.0)
                cobot.waitForTime(1.5)

                # Move to -90
                cobot.moveJoints(q_minus_90, 30.0, 30.0)
                cobot.waitForTime(1.5)

            # Return to home position at the end of the script
            print("Returning back to 0 degree position...")
            cobot.moveJoints(q_home, 30.0, 30.0)
            cobot.waitForTime(1.5)
            
            # >>> STOP DATA LOGGING <<<
            node.is_logging = False
            node.motor_data_csv.flush() # Force write remaining buffer to CSV
            print(">>> STOPPING DATA COLLECTION <<<")
            print("Automated cycle completed.")

        # For disable -> 7, enable -> 8, real -> 9
        elif task_number == 7:
            cobot.disableRobot()
            cobot.waitForTime(0.5)

        elif task_number == 8:
            cobot.enableRobot() # Makes the cobot enable (disengages the brakes)
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
    cobot.initialize(ip, error_callack) 
    print("\n...Robot initialized successfully...\n")

    time.sleep(15)
    print("sleep time over...")
    
    # FT bias setup
    cobot.setFTBiasState(True, 1)
    time.sleep(1)
    cobot.setFTBiasState(False, 1)

    node = MotorTorque_and_Jtsbiased_data(cobot)

    # ROS spin thread
    main_ros_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True
    )
    main_ros_thread.start()

    try:
        # Pass node into user_input so it can toggle the logging flag
        user_input(cobot, node)
    except KeyboardInterrupt:
        print("\033[33m... Aborting, Main Program ... \n\nPlease Wait... \033[0m")
    finally:
        print("Shutting down...")
        time.sleep(0.1)
        node.motor_data_csv.close() # Ensure CSV saves safely
        node.destroy_node()         # destroy ROS node
        rclpy.shutdown()            # shutdown ROS
        cobot.__del__()             # cleanup robot API


if __name__ == "__main__":
    main()
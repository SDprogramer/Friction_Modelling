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
        self.count=1
        self.max_count=100
        self.is_logging=False

     
        self.MotorTorque_data = []
        self.JtsBised_data = []
        self.actual_velocity=[]
        self.joint_state=[]
        self.get_state_data=[]
        # self.task_number=
      
        ## file_path setup and csv initialization 
        
        self.folder_path = "/home/pratap-karmakar/srl06_ros_wrapper/Motor_jts_data_logs/EXP_1"
        os.makedirs(self.folder_path, exist_ok=True)  


        self.timestamp = datetime.now().strftime( "%d.%m.%Y_%H:%M:%S")

        self.file_name = f"J_5_{self.timestamp}.csv"

        self.file_path = os.path.join(
                            self.folder_path,
                            self.file_name)
        
        

        file_exists = os.path.exists(self.file_path)


        self.motor_data_csv=open(self.file_path, "a", newline="")
        self.motor_data_writer=csv.writer(self.motor_data_csv)


        if not file_exists:

                    self.motor_data_writer.writerow([
                            "timestamp",
                            "m_t_1",
                            "m_t_2",
                            "m_t_3",
                            "m_t_4",
                            "m_t_5",
                            "m_t_6",
                            "jts1",
                            "jts2",
                            "jts3",
                            "jts4",
                            "jts5",
                            "jts6",
                            "v1",
                            "v2",
                            "v3",
                            "v4",
                            "v5",
                            "v6",
                            "q1",
                            "q2",
                            "q3",
                            "q4",
                            "q5",
                            "q6"
                        ])


        ## csv file creation for motor_torque 

        ########### publisher creation    
        self.motor_pub = self.create_publisher( 
            Float64MultiArray, "Motor_Torque_data", 10
        )

        self.jts_pub = self.create_publisher(
            Float64MultiArray, "Jts_Biased_data", 10
        )
        
        # self.running = True      
     
        self.read_thread = threading.Thread(
            target=self.timer_loop,
            daemon=True
        )
        self.read_thread.start()   


        # self.current_d_thread=threading.Thread(
        #     target=self.current_data,
        #     daemon=True

            
 
        # ) 

        # self.current_d_thread.start() 

    ######### data read from cobot 
    def read_data(self):  

        m_t =  self.MotorTorque_data = self.cobot.getMotorTorqueData() 
        j_t = self.JtsBised_data = self.cobot.getJTSBiasedData()  

        actual_vel=self.actual_velocity=self.cobot.getJointVelocities()
        joint_state=self.joint_state=self.cobot.getJointValues()
        # robot_state=self.getrobotstate=self.cobot.get


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

            # self.current_data() 

            if self.is_logging :

                timestamp = datetime.now().strftime("%H:%M:%S.%f")     
                            
                current_exp_data=[timestamp] + self.MotorTorque_data + self.JtsBised_data + self.actual_velocity +self.joint_state
                # Bracket has been removed ()
                self.motor_data_writer.writerow(current_exp_data)
                    
            ## timing control  
            now = time.perf_counter()
            sleep_time = next_time - now

            # print(sleep_time)

            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_time = now  

    # def current_data(self):
            
                    
    #             timestamp = datetime.now().strftime("%H:%M:%S")     
                        
    #             current_exp_data=([timestamp] 
    #             + self.MotorTorque_data 
    #             + self.JtsBised_data
    #             + self.actual_velocity
    #             +self.joint_state)

    #             self.motor_data_writer.writerow(current_exp_data)
                        
                        # Current robot snapshot


                    
# =========================
# USER INPUT LOOP
# =========================
def user_input(cobot, node): 
  
    while True:
        time.sleep(0.5)
        
        try:
            
            task_number= int(input("Which task you want to Execute?"
            "\nPress 1 for joint 1"
            "\nPress 2 for joint 2"
            "\nPress 3 for joint 3"
            "\nPress 4 for joint 4"
            "\nPress 5 for joint 5"
            "\nDisable -> 7, Enable -> 8, Real -> 9, Auto -> 10\n"))

        except ValueError: 
            print("Invalid input")
            continue

        print("The Entered Task Number is:",task_number)

        if task_number == 0:    
           print("cobot status...",cobot.getState())

        elif task_number == 1:   
            print("Move Joint 1")
            print("Data logging started...")
               
            node.is_logging=True

            for i in range(3):

                q_pos=[120.0, 0.0, 0.0, 0.0, 0.0, 0.0] # Joint_1 movement 120 degree
                q_neg=[-120.0, 0.0, 0.0, 0.0, 0.0, 00.0] # Joint_1 movement -120 degree

                cobot.moveJoints(q_pos, 30.0, 30.0)
                cobot.waitForTime(1)

                cobot.moveJoints(q_neg, 30.0, 30.0)
                cobot.waitForTime(1)

                print("Cycle no:",(i + 1),"completed...")

            node.is_logging=False
            
            print("use dead man if robot is real ...")
            time.sleep(2)
            cobot.goToHome(30.,30.)
            cobot.waitForTime(0.5)
            

        elif task_number == 2:
            print("Move Joint 2")
            print("Data logging started...")
               
            node.is_logging=True


            for i in range(3):

                q_pos=[0.0, 60.0, 0.0, 0.0, 0.0, 0.0] # Joint_2 movement 60 degree
                q_neg=[0.0, -60.0, 0.0, 0.0, 0.0, 00.0] # Joint_2 movement -60 degree

                cobot.moveJoints(q_pos, 30.0, 30.0)
                cobot.waitForTime(1)

                cobot.moveJoints(q_neg, 30.0, 30.0)
                cobot.waitForTime(1)

                print("Cycle no:",(i + 1),"completed...")

            node.is_logging=False
            
            print("use dead man if robot is real ...")
            time.sleep(2)
            cobot.goToHome(30.,30.)
            cobot.waitForTime(0.5)

        elif task_number == 3: 
            print("Move Joint 3")
            print("Data logging started...")
               
            node.is_logging=True

            for i in range(3):

                q_pos=[0.0, 0.0, 100.0, 0.0, 0.0, 0.0] # Joint_3 movement +100 degree
                q_neg=[0.0, 0.0, -100.0, 0.0, 0.0, 00.0] # Joint_3 movement -100 degree

                cobot.moveJoints(q_pos, 30.0, 30.0)
                cobot.waitForTime(1)

                cobot.moveJoints(q_neg, 30.0, 30.0)
                cobot.waitForTime(1)

                print("Cycle no:",(i + 1),"completed...")

            node.is_logging=False
            
            print("use dead man if robot is real ...")
            time.sleep(2)
            cobot.goToHome(30.,30.)
            cobot.waitForTime(0.5) 
          
        elif task_number == 4: 
            print("Move Joint 4")
            print("Data logging started...")
               
            node.is_logging=True

            for i in range(3):

                q_pos=[0.0, 0.0, 0.0, 120.0, 0.0, 0.0] # Joint_4 movement +120 degree
                q_neg=[0.0, 0.0, 0.0, -120.0, 0.0, 00.0] # Joint_4 movement -120 degree

                cobot.moveJoints(q_pos, 30.0, 30.0)
                cobot.waitForTime(1)

                cobot.moveJoints(q_neg, 30.0, 30.0)
                cobot.waitForTime(1)

                print("Cycle no:",(i + 1),"completed...")

            node.is_logging=False
            
            print("use dead man if robot is real ...")
            time.sleep(2)
            cobot.goToHome(30.,30.)
            cobot.waitForTime(0.5) 
       

        elif task_number == 5: 
            print("Move Joint 5")
            print("Data logging started...")
               
            node.is_logging=True

            for i in range(3):

                q_pos=[0.0, 0.0, 0.0, 0.0, 50.0, 0.0] # Joint_5 movement +100 degree
                q_neg=[0.0, 0.0, 0.0, 0.0, -50.0, 00.0] # Joint_5 movement -100 degree

                cobot.moveJoints(q_pos, 30.0, 30.0)
                cobot.waitForTime(1)

                cobot.moveJoints(q_neg, 30.0, 30.0)
                cobot.waitForTime(1)

                print("Cycle no:",(i + 1),"completed...")

            node.is_logging=False
            
            print("use dead man if robot is real ...")
            time.sleep(2)
            cobot.goToHome(30.,30.)
            cobot.waitForTime(0.5) 
 
        elif task_number == 6: 
            print("Move Joint 6")
            print("Data logging started...")

        
            node.is_logging=True

            for i in range(3):

                q_pos=[0.0, 0.0, 0.0, 0.0, 0.0, 90.0] # Joint_6 movement +90 degree
                q_neg=[0.0, 0.0, 0.0, 0.0, 0.0, -90.0] # Joint_6 movement -90 degree

                cobot.moveJoints(q_pos, 30.0, 30.0)
                cobot.waitForTime(1)

                cobot.moveJoints(q_neg, 30.0, 30.0)
                cobot.waitForTime(1)

                print("cycle no:",(i + 1),"completed...")

            node.is_logging=False
            
            print("use dead man if robot is real ...")
            time.sleep(2)
            cobot.goToHome(30.,30.)
            cobot.waitForTime(0.5)    
                
        # For disable -> 7, enable -> 8, real -> 9 ,
        elif task_number == 7:
            cobot.disableRobot()
            cobot.waitForTime(0.5)

        elif task_number == 8:
            cobot.enableRobot() # Makes the cobot enable (disengages the brakes)
            cobot.waitForTime(0.5)

        elif task_number == 9:
            cobot.switchToReal()
            cobot.waitForTime(0.5)

        elif task_number == 10:
             cobot.switchToAuto()
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
   
    time.sleep(10)
   
    print("sleep time over...")

    
    # FT bias setup
    cobot.setFTBiasState(True, 1)
    time.sleep(1)
    cobot.setFTBiasState(False, 1)
    # get_logger().info("FT sensor biased")

    node = MotorTorque_and_Jtsbiased_data(cobot)

    # ROS spin thread
    main_ros_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True
    )
    main_ros_thread.start()

    try:
        user_input(cobot,node)


    except KeyboardInterrupt:
        print("\033[33m... Aborting, Main Program ... \n\nPlease Wait... \033[0m")
        
    finally:
        print("Shutting down...")

        time.sleep(0.1)
      
        node.destroy_node()      # destroy ROS node
        rclpy.shutdown()         # shutdown ROS
        cobot.__del__()          # cleanup robot API


if __name__ == "__main__":
    main()
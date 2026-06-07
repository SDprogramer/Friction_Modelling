import time
import csv
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from SvayaAPI.clientApi import SvayaApi
import threading
import os
from datetime import datetime

ip = "192.168.20.203"

def error_callack(error_priority, error_msg, error_status):
    print("Error: ", error_priority, error_msg, error_status)

class MotorTorque_and_Jtsbiased_data(Node):

    def __init__(self, cobot):
        super().__init__('MotorTorque_and_Jtsbiased_data')

        self.cobot = cobot

        self.MotorTorque_data = []
        self.JtsBised_data = []
        self.actual_velocity = []
        self.joint_state = []

        # CSV file handles: one per joint, created on first use
        self._csv_writers = {}   # task_number -> csv.writer
        self._csv_files  = {}    # task_number -> file handle

        self.folder_path = "/home/pratap-karmakar/srl06_ros_wrapper/Motor_jts_data_logs/EXP_1"
        os.makedirs(self.folder_path, exist_ok=True)

        # Publishers
        self.motor_pub = self.create_publisher(Float64MultiArray, "Motor_Torque_data", 10)
        self.jts_pub   = self.create_publisher(Float64MultiArray, "Jts_Biased_data",   10)

        self.read_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.read_thread.start()

    # ── open (or reuse) the CSV for this joint ──────────────────────────────
    def _get_writer(self, task_number):
        if task_number not in self._csv_writers:
            # File name fixed at first call for this joint in this session
            timestamp = datetime.now().strftime("%d.%m.%Y_%H_%M_%S")
            file_name  = f"J{task_number}_{timestamp}.csv"
            file_path  = os.path.join(self.folder_path, file_name)

            f = open(file_path, "a", newline="")
            writer = csv.writer(f)

            # Write header only for a brand-new file
            if os.path.getsize(file_path) == 0:
                writer.writerow([
                    "timestamp",
                    "m_t_1","m_t_2","m_t_3","m_t_4","m_t_5","m_t_6",
                    "jts1","jts2","jts3","jts4","jts5","jts6",
                    "v1","v2","v3","v4","v5","v6",
                    "q1","q2","q3","q4","q5","q6"
                ])

            self._csv_files[task_number]   = f
            self._csv_writers[task_number] = writer
            self.get_logger().info(f"Opened CSV: {file_path}")

        return self._csv_writers[task_number]

    # ── read from cobot ──────────────────────────────────────────────────────
    def read_data(self):
        self.MotorTorque_data  = self.cobot.getMotorTorqueData()
        self.JtsBised_data     = self.cobot.getJTSBiasedData()
        self.actual_velocity   = self.cobot.getJointVelocities()
        self.joint_state       = self.cobot.getJointValues()

    # ── publish ──────────────────────────────────────────────────────────────
    def publish_data(self):
        msg1 = Float64MultiArray(); msg1.data = self.MotorTorque_data
        self.motor_pub.publish(msg1)

        msg2 = Float64MultiArray(); msg2.data = self.JtsBised_data
        self.jts_pub.publish(msg2)

    # ── 200 Hz loop ──────────────────────────────────────────────────────────
    def timer_loop(self):
        period    = 0.005
        next_time = time.perf_counter()

        while rclpy.ok():
            next_time += period
            self.read_data()
            self.publish_data()

            sleep_time = next_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_time = time.perf_counter()

    # ── append one row for the given joint ──────────────────────────────────
    def current_data(self, task_number):
        writer = self._get_writer(task_number)
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]   # ms precision

        row = (
            [timestamp]
            + list(self.MotorTorque_data)
            + list(self.JtsBised_data)
            + list(self.actual_velocity)
            + list(self.joint_state)
        )
        writer.writerow(row)
        self._csv_files[task_number].flush()   # make sure it hits disk

    # ── cleanup ──────────────────────────────────────────────────────────────
    def close_all_files(self):
        for f in self._csv_files.values():
            f.close()


# =============================================================================
# USER INPUT LOOP
# =============================================================================
def user_input(cobot, node):

    while True:
        time.sleep(0.2)

        try:
            task_number = int(input(
                "\nWhich task to execute?\n"
                "  1-6 → joint movement  |  7 → disable  |  8 → enable  |  9 → real  |  99 → quit\n"
                "> "
            ))
        except ValueError:
            print("Invalid input — enter a number.")
            continue

        print(f"Task: {task_number}")

        if task_number == 0:
            print("Cobot state:", cobot.getState())

        elif 1 <= task_number <= 5:
            print(f"Move Joint {task_number}")
            node.current_data(task_number)

        elif task_number == 6:
            print("Move Joint 6 — logging data...")

            q_pos = [0.0, 0.0, 0.0, 0.0, 0.0,  90.0]
            q_neg = [0.0, 0.0, 0.0, 0.0, 0.0, -90.0]

            for cycle in range(3):
                print(f"  Cycle {cycle+1}/3 → +90°")
                cobot.moveJoints(q_pos, 30.0, 30.0)

                # Log continuously while robot moves (~1 s at 200 Hz → ~200 rows)
                t_end = time.perf_counter() + 1.0
                while time.perf_counter() < t_end:
                    node.current_data(task_number)
                    time.sleep(0.005)

                print(f"  Cycle {cycle+1}/3 → -90°")
                cobot.moveJoints(q_neg, 30.0, 30.0)

                t_end = time.perf_counter() + 1.0
                while time.perf_counter() < t_end:
                    node.current_data(task_number)
                    time.sleep(0.005)

            print("Done. Rows written:", sum(1 for _ in open(
                list(node._csv_files.values())[-1].name)))

        elif task_number == 7:
            cobot.disableRobot(); cobot.waitForTime(0.5)

        elif task_number == 8:
            cobot.enableRobot();  cobot.waitForTime(0.5)

        elif task_number == 9:
            cobot.switchToReal(); cobot.waitForTime(0.5)

        elif task_number == 99:
            cobot.disableRobot()
            break

        else:
            print("Invalid task number.")


# =============================================================================
# MAIN
# =============================================================================
def main():
    rclpy.init()

    cobot = SvayaApi()
    # cobot.initialize(ip, error_callack)
    print("\n...Robot initialized successfully...\n")

    node = MotorTorque_and_Jtsbiased_data(cobot)

    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()

    try:
        user_input(cobot, node)

    except KeyboardInterrupt:
        print("\033[33m\n... Aborting ...\033[0m")

    finally:
        print("Shutting down...")
        node.close_all_files()
        time.sleep(0.1)
        node.destroy_node()
        rclpy.shutdown()
        cobot.__del__()


if __name__ == "__main__":
    main()
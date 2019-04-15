import simpy
import numpy
import pandas as pd
import math

class tables:
    def __init__(self,env,machine_list):
        #create variables bound to instance
        CreatVariable=locals()
        #Initialize the production setting
        self.env = env
        self.O=machine_list[0]
        self.A=machine_list[1]
        self.B=machine_list[2]
        self.C=machine_list[3]
        self.D=machine_list[4]
        self.E=machine_list[5]
        self.F=machine_list[6]
        self.G=machine_list[7]

    def throughput_tracker(self):
        while True:
            #product 0
            # self.P0S0_throughput=self.O.throughputstamp[-1] #product 0 stage 0
            # self.P0S1_throughput=self.A.throughputstamp[-1]
            # self.P0S2_throughput=self.C.throughputstamp_0[-1]+self.D.throughputstamp_0[-1]
            # self.P0S3_throughput=self.E.throughputstamp[-1]+self.G.throughputstamp[-1]
            #
            #
            # #product 1
            # self.P1S1_throughput=self.B.throughputstamp[-1]
            # self.P1S2_throughput=self.C.throughputstamp_1[-1]+self.D.throughputstamp_1[-1]
            # self.P1S3_throughput=self.F.throughputstamp[-1]
            yield self.env.timeout(2)

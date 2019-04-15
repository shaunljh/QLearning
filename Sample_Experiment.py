import simpy
import Flexi_Machine
import Single_Machine
import matplotlib.pyplot as plt
import numpy as np
import RL_selection
import RL_shutdown_single_machine
import math
import seaborn as sns
import Tables
import RL_shutdown_split_machine
import pandas as pd

sns.set()

class shopfloor:
    def __init__(self,env):
        #STEP 1: Specify the environment for instances
        self.env=env
        self.time=4000
        #STEP 2: Create instances of machines within the factory
        self.Machine_O=Single_Machine.single_machine(env,1,5,10000,250,'Machine_O','Tube',0)
        self.Machine_A=Single_Machine.single_machine(env,2,5,10000,250,'Machine_A','Tube',0)
        self.Machine_B=Single_Machine.single_machine(env,4,5,10000,250,'Machine_B','Plate',1)
        self.Bottle_Neck_C=Flexi_Machine.flexi_machine(env,50000,250,'Bottle_Neck_C')
        self.Bottle_Neck_D=Flexi_Machine.flexi_machine(env,50000,250,'Bottle_Neck_D')
        self.Machine_E=Single_Machine.single_machine(env,4,4,1000,250,'Machine_E','Tube',0)
        self.Machine_F=Single_Machine.single_machine(env,2,4,3000,250,'Machine_F','Plate',1)
        self.Machine_G=Single_Machine.single_machine(env,4,4,2000,250,'Machine_G','Tube',0)
        self.Tables=Tables.tables(env,[self.Machine_O,self.Machine_A,self.Machine_B,self.Bottle_Neck_C,self.Bottle_Neck_D,self.Machine_E,self.Machine_F,self.Machine_G])


        #STEP 3: Set the sequence of the machine, specify its upstream and downstream machines
        #MUST USE "None" if there is NO upstream/downstream machine
        self.Machine_O.sequence(None,[self.Machine_A],self.Tables)
        self.Machine_A.sequence([self.Machine_O],[self.Bottle_Neck_C,self.Bottle_Neck_D],self.Tables)
        self.Machine_B.sequence(None,[self.Bottle_Neck_C,self.Bottle_Neck_D],self.Tables)
        self.Machine_E.sequence([self.Bottle_Neck_C,self.Bottle_Neck_D],None,self.Tables)
        self.Machine_F.sequence([self.Bottle_Neck_C,self.Bottle_Neck_D],None,self.Tables)
        self.Machine_G.sequence([self.Bottle_Neck_C,self.Bottle_Neck_D],None,self.Tables)
        self.Bottle_Neck_C.parameters(['Tube','Plate'],[self.Machine_A, self.Machine_B],\
        [self.Machine_E,self.Machine_F,self.Machine_G],[4,9],[5,5],self.Tables)
        self.Bottle_Neck_D.parameters(['Tube','Plate'],[self.Machine_A, self.Machine_B],\
        [self.Machine_E,self.Machine_F,self.Machine_G],[5,10],[5,5],self.Tables)

        #add selection algorithm
        self.Brain_C=RL_selection.Brain(self.env,self.Bottle_Neck_C,\
        [self.Machine_A,self.Machine_B],[self.Machine_E,self.Machine_F,self.Machine_G],'Primary')
        self.Brain_D=RL_selection.Brain(self.env,self.Bottle_Neck_D,\
        [self.Machine_A,self.Machine_B],[self.Machine_E,self.Machine_F,self.Machine_G],self.Brain_C)


        #add shutdown algorithm
        self.Brain_O=RL_shutdown_split_machine.Brain(self.env,self.Machine_O,[self.Machine_A,self.Machine_B]\
        ,[self.Bottle_Neck_C,self.Bottle_Neck_D],[self.Machine_E,self.Machine_F,self.Machine_G],0,0)
        self.Brain_A=RL_shutdown_split_machine.Brain(self.env,self.Machine_A,[self.Machine_A,self.Machine_B]\
        ,[self.Bottle_Neck_C,self.Bottle_Neck_D],[self.Machine_E,self.Machine_F,self.Machine_G],0,1)
        self.Brain_B=RL_shutdown_split_machine.Brain(self.env,self.Machine_B,[self.Machine_A,self.Machine_B]\
        ,[self.Bottle_Neck_C,self.Bottle_Neck_D],[self.Machine_E,self.Machine_F,self.Machine_G],1,1)
        self.Brain_E=RL_shutdown_split_machine.Brain(self.env,self.Machine_E,[self.Machine_A,self.Machine_B]\
        ,[self.Bottle_Neck_C,self.Bottle_Neck_D],[self.Machine_E,self.Machine_F,self.Machine_G],0,3)
        self.Brain_F=RL_shutdown_split_machine.Brain(self.env,self.Machine_F,[self.Machine_A,self.Machine_B]\
        ,[self.Bottle_Neck_C,self.Bottle_Neck_D],[self.Machine_E,self.Machine_F,self.Machine_G],1,3)
        self.Brain_G=RL_shutdown_split_machine.Brain(self.env,self.Machine_G,[self.Machine_A,self.Machine_B]\
        ,[self.Bottle_Neck_C,self.Bottle_Neck_D],[self.Machine_E,self.Machine_F,self.Machine_G],0,3)

        #STEP 4: Specify the process function for each instances
        #self.env.process(self.Machine_O.production())
        self.env.process(self.Machine_O.production())
        self.env.process(self.Machine_O.performance_tracking())
        self.env.process(self.Machine_A.production())
        self.env.process(self.Machine_A.performance_tracking())
        self.env.process(self.Machine_B.production())
        self.env.process(self.Machine_B.performance_tracking())
        self.env.process(self.Bottle_Neck_C.production())
        self.env.process(self.Bottle_Neck_C.performance_tracking())
        self.env.process(self.Bottle_Neck_D.production())
        self.env.process(self.Bottle_Neck_D.performance_tracking())
        self.env.process(self.Machine_E.production())
        self.env.process(self.Machine_E.performance_tracking())
        self.env.process(self.Machine_F.production())
        self.env.process(self.Machine_F.performance_tracking())
        self.env.process(self.Machine_G.production())
        self.env.process(self.Machine_G.performance_tracking())
        self.env.process(self.Tables.throughput_tracker())


        #Stage 3 Sample Experiment on Machine F
        self.env.process(self.Machine_F.slowdown(4000,2000))


#STEP 5: Create the instance of class "Environment"
env=simpy.Environment()

#STEP 6: Create the instance of class "Shopfloor"
spf=shopfloor(env)

#STEP 7: Start the simulation
spf.env.run(spf.time)


#STEP 8: Data Processing
print('Machine O:',spf.Machine_O.shd,'shutdown time',spf.Machine_O.cumulated_shutdown_time,'starvetime',spf.Machine_O.starve_time)
print('Machine A:',spf.Machine_A.shd,'shutdown time',spf.Machine_A.cumulated_shutdown_time,'starvetime',spf.Machine_A.starve_time)
print('Machine B:',spf.Machine_B.shd,'shutdown time',spf.Machine_B.cumulated_shutdown_time,'starvetime',spf.Machine_B.starve_time)
print('Machine E:',spf.Machine_E.shd,'shutdown time',spf.Machine_E.cumulated_shutdown_time,'starvetime',spf.Machine_E.starve_time)
print('Machine F:',spf.Machine_F.shd,'shutdown time',spf.Machine_F.cumulated_shutdown_time,'starvetime',spf.Machine_F.starve_time)
print('Machine G:',spf.Machine_G.shd,'shutdown time',spf.Machine_G.cumulated_shutdown_time,'starvetime',spf.Machine_G.starve_time)
print('Product 0 output',spf.Machine_E.output+spf.Machine_G.output)
print('Product 1 output',spf.Machine_F.output)
print('Product 0 bottleneck at stage',spf.Brain_A.bottle_neck_index+1)
print('Product 1 bottleneck at stage',spf.Brain_B.bottle_neck_index+1)

#Sample Plot
plt.figure(figsize=(12,6))
plt.plot(spf.Machine_A.timestamp,spf.Machine_A.queuestamp_0,label='Machine A, Product 0',color='firebrick',linewidth=1)
plt.plot(spf.Machine_E.timestamp,spf.Machine_E.queuestamp_0,label='Machine E, Product 0',color='blue',linewidth=1)
plt.plot(spf.Machine_F.timestamp,spf.Machine_F.queuestamp_1,label='Machine F, Product 1',color='orangered',linewidth=1)
plt.plot(spf.Machine_G.timestamp,spf.Machine_G.queuestamp_0,label='Machine G, Product 0',color='darkorchid',linewidth=1)
plt.xlabel('Time')
plt.xlim(1500,4000)
plt.ylabel('Machine Queue')
plt.ylim(0,100)
plt.legend()
plt.title('Plot of Individual Machine Queue Status against Time')

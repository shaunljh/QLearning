import simpy
import numpy
import pandas as pd
import math

class Brain:
    def __init__(self,env,target,stage_1,stage_2,stage_3,product_index,self_stage):
        #initialize the environment and target
        self.env=env
        self.target=target
        self.product_index=product_index
        self.stage_1=stage_1
        self.stage_2=stage_2
        self.stage_3=stage_3
        self.self_stage=self_stage
        self.pt_list=[]
        self.throughput_list=[]
        self.bottle_neck_throughput=1
        self.bottle_neck_index=1
        self.bottle_neck_std=1
        self.shutdown_T=0
        self.queue_status=[]
        self.shutdown_proportion=[]

        #initialize the control parameters bound to the target
        self.base_duration=60
        self.current_duration=60
        self.cumulative_running_time=0
        self.time_record=[]
        self.time_all=[]
        self.duration_record=[]
        self.cost_record=[]
        self.periodic_utilization_record=[]

        #Initialize the Q-Learning Algorithm
        n_state=14400
        n_actions = 3
        actions = ['minus','keep','add']
        self.q_duration_table_up = pd.DataFrame(numpy.zeros((n_state,len(actions))),columns=actions)
        self.q_duration_table_down = pd.DataFrame(numpy.zeros((n_state,len(actions))),columns=actions)
        self.table_list=[self.q_duration_table_up,self.q_duration_table_down,self.q_duration_table_down]

        #parameter setting
        self.EPSILON=0.8
        self.LAMBDA=0.8
        self.ALPHA=0.8

        self.new_cycle=self.env.event()

        #fill the monitoring function to process method
        self.env.process(self.cycle_process())
        self.env.process(self.QL_process())

    def cycle_process(self):
        while True:
            yield self.new_cycle
            #calculate the actual shutdown time
            production_T=self.required_output * self.target.expected_pt
            safety_T=1.64 * math.sqrt(self.required_output) * self.target.expected_pt_std
            shutdown_T=self.base_duration - production_T - safety_T
            self.shutdown_T=shutdown_T
            print(self.target.label,'production T',production_T,'safety time',safety_T,'shutdown T',shutdown_T)

            #if shutdown time is positive, means able to shutdown
            if shutdown_T>0:
                self.current_duration=self.base_duration
                yield self.env.timeout(production_T + safety_T)
                if self.target.shutdown_event.triggered==False:
                    self.target.shutdown_event.succeed()
                yield self.env.timeout(shutdown_T)
                if self.target.shutdown_ended_event.triggered==False:
                    self.target.shutdown_ended_event.succeed()

                #update the shutdown plan for next round
                self.data()
            else:
                #DO NOT shutdown machine, and extend the current duration
                self.current_duration= production_T + safety_T
            self.data()
            self.new_cycle=self.env.event()

    #Contineous monitoring and learning
    def QL_process(self):
        #let machines run for a while atbthe beginning
        yield self.env.timeout(20)
        while True:
            #base time unit is 1 for monitoring
            yield self.env.timeout(0.1)
            self.cumulative_running_time+=0.1
            #update the production states  and q-table every time unit
            self.status_update()
            self.QL(self.use_which_table())
            self.data_2()

            #finish current duration (for scheduled shutdown) and start a new round
            if self.cumulative_running_time-self.current_duration>0.5:
                print('new cycle started!!!!',self.target.label,self.env.now)
                print(self.target.label,"required output is:", self.required_output, "bottle neck queue is:",self.queue_status[self.bottle_neck_index])

                self.new_cycle.succeed()
                self.cumulative_running_time=0

    def status_update(self):
        #update the processing time
        #stage 1 product 0
        throughput_stage_1_0=self.stage_1[0].expected_throughput
        throughput_std_1_0=[self.stage_1[0].expected_throughput_std]
        #stage 2 product 0
        throughput_stage_2_0=self.stage_2[0].expected_throughput_0+self.stage_2[1].expected_throughput_0
        throughput_std_2_0=[self.stage_2[0].expected_throughput_std_0,self.stage_2[1].expected_throughput_std_0]
        #stage 3 product 0
        throughput_stage_3_0=self.stage_3[0].expected_throughput+self.stage_3[2].expected_throughput
        throughput_std_3_0=[self.stage_3[0].expected_throughput_std,self.stage_3[2].expected_throughput_std]
        throughput_list_0=[throughput_stage_1_0,throughput_stage_2_0,throughput_stage_3_0]
        std_list_0=[throughput_std_1_0,throughput_std_2_0,throughput_std_3_0]

        #stage 1 product 1
        throughput_stage_1_1=self.stage_1[1].expected_throughput
        throughput_std_1_1=[self.stage_1[1].expected_throughput_std]
        #stage 2 product 1
        throughput_stage_2_1=self.stage_2[0].expected_throughput_1+self.stage_2[1].expected_throughput_1
        throughput_std_2_1=[self.stage_2[0].expected_throughput_std_1,self.stage_2[1].expected_throughput_std_1]
        #stage 3 product 1
        throughput_stage_3_1=self.stage_3[1].expected_throughput
        throughput_std_3_1=[self.stage_3[1].expected_throughput_std]
        throughput_list_1=[throughput_stage_1_1,throughput_stage_2_1,throughput_stage_3_1]
        #compiling throughput
        std_list_1=[throughput_std_1_1,throughput_std_2_1,throughput_std_3_1]

        if self.product_index==0:
            self.bottle_neck_index=numpy.argmin(throughput_list_0)
            self.bottle_neck_throughput=min(throughput_list_0)
            self.bottle_neck_std=std_list_0[self.bottle_neck_index]
            stage_1_queue=self.stage_1[0].queue[0]
            stage_2_queue=self.stage_2[0].queue[0]+self.stage_2[1].queue[0]
            stage_3_queue=self.stage_3[0].queue[0]+self.stage_3[2].queue[0]
            self.queue_status=[stage_1_queue,stage_2_queue,stage_3_queue]

        if self.product_index==1:
            self.bottle_neck_index=numpy.argmin(throughput_list_1)
            self.bottle_neck_throughput=min(throughput_list_1)
            self.bottle_neck_std=std_list_1[self.bottle_neck_index]
            stage_1_queue=self.stage_1[1].queue[1]
            stage_2_queue=self.stage_2[0].queue[1]+self.stage_2[1].queue[1]
            stage_3_queue=self.stage_3[1].queue[1]
            self.queue_status=[stage_1_queue,stage_2_queue,stage_3_queue]


    def use_which_table(self):
        return self.table_list[self.bottle_neck_index]

    def duration_cost_calculator(self,queue_cost_per_unit,shutdown_cost):
        #calculate the bottleneck machine's expected usage during the duration
        running_ratio=self.target.expected_throughput/self.bottle_neck_throughput
        expected_output=self.base_duration * self.bottle_neck_throughput
        expected_safety_stock=0
        #when bottleneck is after me
        if (self.bottle_neck_index+1)>self.self_stage:
            #calculate the safety stock of downstream machine during whole duration, 95% here
            for j in range(len(self.bottle_neck_std)):
                expected_safety_stock+=self.bottle_neck_std[j]*1.64*math.sqrt(self.base_duration)
            average_queue= expected_output/2 + expected_safety_stock
            if self.self_stage==0:
                self.required_output=max(0,2+math.ceil(expected_output + expected_safety_stock - self.queue_status[0]+1))
            else:
                self.required_output=max(0,2+math.ceil(expected_output + expected_safety_stock - self.queue_status[self.bottle_neck_index]))

        #when bottleneck is before me
        elif self.self_stage==3 and self.product_index==0:

            if self.target.label=='Machine_E':
                self.required_output=max(0,expected_output/2-self.stage_3[2].expected_throughput+self.stage_3[0].queue[self.product_index])
            else:
                self.required_output=max(0,expected_output/2-self.stage_3[0].expected_throughput+self.stage_3[2].queue[self.product_index])

            average_queue=self.required_output/2

        elif self.self_stage==3 and self.product_index==1:
            self.required_output=max(0,expected_output/2+self.stage_3[1].queue[self.product_index])
            average_queue=self.required_output/2

        else:
            #then the required output is equal to the output of upstream machine
            self.required_output=expected_output

            #when bottleneck is before me, I need to manage the queue of myself
            average_queue= expected_output/2

        #Average shutdown per day
        average_shutdown=1440/self.base_duration

        #calculate the daily cost of shutdown and WIP
        total_cost_queue = queue_cost_per_unit * average_queue
        total_cost_shutdown = shutdown_cost * average_shutdown
        total_cost_running = running_ratio* 2
        self.duration_cost= total_cost_queue + total_cost_shutdown + total_cost_running

        return(self.duration_cost)

    def QL(self,table):
        self.S=self.base_duration
        cost_now=self.duration_cost_calculator(2,1)
        self.ACTIONS = ['minus','keep','add']
        self.A = self.choose_action(table)
        S_next= self.action()
        self.base_duration=S_next
        #after determined the action, determine the reward for that move
        cost_next=self.duration_cost_calculator(2,1)

        rwd=cost_now-cost_next
        q_predict = table.ix[self.S,self.A]
        q_target = rwd + self.LAMBDA*table.iloc[S_next,:].max()
        table.ix[self.S,self.A] = (1-self.ALPHA) * (q_predict)+self.ALPHA*(q_target)
        self.S = S_next

    def choose_action(self,table):
        state_action = table.iloc[self.base_duration,:]
        if (numpy.random.uniform() > self.EPSILON) or (state_action.all() == 0):
            self.action_name = numpy.random.choice(self.ACTIONS)
        else:
            self.action_name = state_action.idxmax()
        return self.action_name

    def action(self):
        if self.A == 'add':
            if self.S>=500:
                S_next=500
            else:
                S_next = self.S + 1
        elif self.A=='minus':
            if self.S == 1:
                S_next = self.S
            else:
                S_next = self.S - 1
        else:
            S_next =self.S
        return S_next

    def data(self):
        self.time_record.append(self.env.now)
        self.shutdown_proportion.append(max(self.shutdown_T,0)/self.base_duration)
        self.duration_record.append(self.base_duration)
        print ('base duration is:',self.base_duration)

    def data_2(self):
        self.time_all.append(self.env.now)
        self.cost_record.append(self.duration_cost)

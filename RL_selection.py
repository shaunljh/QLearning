import simpy
import numpy
import pandas as pd
import math


class Brain:
    def __init__(self,env,target,upstream_list,downstream_list,link):
        #initialize the environment and target
        CreatVariable=locals()

        self.env=env
        self.target=target
        self.upstream_list=upstream_list
        self.downstream_list=downstream_list
        self.lotsize_0=10
        self.lotsize_1=10
        self.fixed_cost=50
        self.wip_cost=0.1
        self.reward=0
        self.pri_throughput_0=0
        self.pri_throughput_1=0
        self.link=link

        #initialize the control parameters bound to the target
        self.upstream_pt_list=[]
        self.downstream_pt_list=[]
        self.production_plan=[self.lotsize_0,self.lotsize_1]

        self.upstream_throughput_list=[]
        self.downstream_throughput_list=[]
        self.rew=[]

        self.portion=50

        #Initialize the Q-Learning Algorithm
        n_state=100
        n_actions = 3
        actions = ['minus','keep','add']
        self.q_portion_table = pd.DataFrame(numpy.zeros((n_state,len(actions))),columns=actions)

        self.EPSILON=0.8
        self.LAMBDA=0.8
        self.ALPHA=0.8

        #initialize teh data collection
        self.time=[]
        self.q_value=[]

        self.env.process(self.tick_tock())

    #Contineous monitoring and learning
    def tick_tock(self):
        while True:
            #base time unit is 1 for monitoring
            yield self.env.timeout(0.1)
            self.data()
            self.status_update()
            self.QL(self.q_portion_table)
            self.target.qportion=self.portion/100
            self.target.production_plan[0]=self.production_plan[0]
            self.target.production_plan[1]=self.production_plan[1]
            self.target.expected_pt_0=(self.target.production_plan[0]*self.target.process_time_list[0]\
            +self.target.production_plan[1]*self.target.process_time_list[1])/(self.target.production_plan[0])
            self.target.expected_pt_1=(self.target.production_plan[0]*self.target.process_time_list[0]\
            +self.target.production_plan[1]*self.target.process_time_list[1])/(self.target.production_plan[1])
            self.target.expected_throughput_0=1/self.target.expected_pt_0
            self.target.expected_throughput_1=1/self.target.expected_pt_1


    def status_update(self):
        #update the status of connected machines
        self.upstream_pt_list=[self.upstream_list[i].expected_pt for i in range(2)]
        self.downstream_pt_list=[self.downstream_list[i].expected_pt for i in range(3)]

        self.upstream_throughput_list=[self.upstream_list[i].throughput for i in range(2)]
        self.downstream_throughput_list=[self.downstream_list[i].throughput for i in range(3)]


    def portion_throughput_calculator(self,profit_1,profit_2):

        portion=self.portion/100

        #calculate the expected throughput for the machine itself under current portion
        expected_throughput=1/(portion*self.target.process_time_list[0]\
        +(1-portion)*self.target.process_time_list[1])

        #calculate the expected throughput and income of downstream machines
        self.pri_throughput_0=portion/(portion*self.target.process_time_list[0]\
        +(1-portion)*self.target.process_time_list[1])

        self.pri_throughput_1=(1-portion)/(portion*self.target.process_time_list[0]\
        +(1-portion)*self.target.process_time_list[1])

        if self.link=='Primary':

            if (1/self.downstream_pt_list[0]+1/self.downstream_pt_list[2])<self.pri_throughput_0:
                self.pri_throughput_0=(1/self.downstream_pt_list[0]+1/self.downstream_pt_list[2])
            if 1/self.downstream_pt_list[1]<self.pri_throughput_1:
                self.pri_throughput_1=1/self.downstream_pt_list[1]
            income_1=profit_1*self.pri_throughput_0
            income_2=profit_2*self.pri_throughput_1
            sum_expected_income= income_1 + income_2

            portion_rwd = sum_expected_income

        else:

            if (1/self.downstream_pt_list[0]+1/self.downstream_pt_list[2])-self.link.pri_throughput_0<self.pri_throughput_0:
                self.pri_throughput_0=(1/self.downstream_pt_list[0]+1/self.downstream_pt_list[2])-self.link.pri_throughput_0
            if (1/self.downstream_pt_list[1])-self.link.pri_throughput_1<self.pri_throughput_1:
                self.pri_throughput_1=1/self.downstream_pt_list[1]-self.link.pri_throughput_1
            income_1=profit_1*self.pri_throughput_0
            income_2=profit_2*self.pri_throughput_1
            sum_expected_income= income_1 + income_2


            portion_rwd = sum_expected_income

        return(portion_rwd)



    def QL(self,table):
        #calculate the current expected income
        self.S=self.portion

        reward_now=self.portion_throughput_calculator(40,80)
        test=reward_now
        cost_now=self.cost_calculator(self.portion)
        reward_now-=cost_now
        self.reward=reward_now

        self.ACTIONS = ['minus','keep','add']
        self.A = self.choose_action(table)
        S_next= self.action()

        #after determining the action, determine the expected income for next state
        self.portion=S_next
        reward_next=self.portion_throughput_calculator(40,80)

        if self.A == 'keep':
            cost_next=cost_now
        else:
            cost_next=self.cost_calculator(self.portion)

        reward_next-=cost_next

        #calculate the reward for that move and update q table
        rwd=reward_next-reward_now
        q_predict = table.ix[self.S,self.A]
        q_target = rwd + self.LAMBDA*table.iloc[S_next,:].max()
        table.ix[self.S,self.A] = (1-self.ALPHA) * (q_predict)+self.ALPHA*(q_target)
        self.S = S_next


    def cost_calculator(self,portion):
        portion=portion/100
        #Initialize loop for lot size
        lowest_cost=999999
        lotsize_coefficient=0.01
        while lotsize_coefficient<2:
            lotsize_0=math.ceil(self.portion*lotsize_coefficient) #update lotsizes
            lotsize_1=math.ceil((100-self.portion)*lotsize_coefficient) #update lotsizes

            set_up_cost=(2*self.fixed_cost)/(self.target.process_time_mean_list[0]\
            *lotsize_0+self.target.process_time_mean_list[1]*lotsize_1)

            inv_worst_case_0=lotsize_0*(0.5*self.target.process_time_mean_list[0]*lotsize_0\
            +lotsize_1*self.target.process_time_mean_list[1])/(lotsize_0*self.target.process_time_mean_list[0]\
            +lotsize_1*self.target.process_time_mean_list[1])

            inv_worst_case_1=lotsize_1*(0.5*self.target.process_time_mean_list[1]*lotsize_1\
            +lotsize_0*self.target.process_time_mean_list[0])/(lotsize_0*self.target.process_time_mean_list[0]\
            +lotsize_1*self.target.process_time_mean_list[1])

            inv_worst_case=inv_worst_case_0+inv_worst_case_1
            inv_best_case=0
            inv_cost=(inv_best_case+inv_worst_case)/2

            current_cost=set_up_cost+inv_cost

            if current_cost<lowest_cost:
                lowest_cost=current_cost
                coefficient_chosen=lotsize_coefficient

            lotsize_coefficient+=0.02

        self.lotsize_0=math.ceil(self.portion*coefficient_chosen) #update lotsizes
        self.lotsize_1=math.ceil((100-self.portion)*coefficient_chosen)#update lotsizes
        self.production_plan=[self.lotsize_0,self.lotsize_1]

        return (lowest_cost)


    def choose_action(self,table):
        position=self.portion
        state_action = table.iloc[position,:]
        if (numpy.random.uniform() > self.EPSILON) or (state_action.all() == 0):
            self.action_name = numpy.random.choice(self.ACTIONS)
        else:
            self.action_name = state_action.argmax()
        return self.action_name

    def action(self):
        if self.A == 'add':
            S_next = self.S + 1
            if self.S == 99:
                S_next = self.S
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
        self.time.append(self.env.now)
        self.rew.append(self.reward)
        self.q_value.append(self.portion)

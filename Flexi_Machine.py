import simpy
import random
import numpy

class flexi_machine:
    def __init__(self,env,MTBF,MTTR,label):
        #create variables bound to instance
        CreatVariable=locals()
        #Initialize the production setting
        self.env = env
        self.mtbf = MTBF
        self.mttr = MTTR
        self.label = label


        #Initialize the possible events during production
        self.feed=self.env.event()
        self.sufficient_stock=self.env.event()
        self.sufficient_stock_0=self.env.event()
        self.sufficient_stock_1=self.env.event()

        self.working_event=self.env.event()
        self.shutdown_event=self.env.event()

        #Initialize the events'states
        self.sufficient_stock.succeed()
        self.sufficient_stock_0.succeed()
        self.sufficient_stock_1.succeed()
        self.working_event.succeed()

        #Initialize the control parameters
        self.cumulated_running_time = 0 #for MTBF
        self.total_running_time = 0 #for performance tracking
        self.production_plan = [8,8] #for lotsizes
        self.production_counter=[5,5]
        self.shutdown_time=0
        self.bkd=0 #breakdown counter
        self.bkd_time=0
        self.qportion=0.5
        self.mportion=0.5
        self.q=0
        self.m=0
        self.expected_pt_0=1
        self.expected_throughput_0=1
        self.expected_pt_1=1
        self.expected_throughput_1=1
        self.throughput_0_std_counter=[]
        self.throughput_1_std_counter=[]
        self.expected_throughput_std_0=1
        self.expected_throughput_std_1=1
        self.output_0=0
        self.output_1=0
        self.cutoff_0=False
        self.cutoff_1=False
        self.timestamp=[]
        self.throughputstamp_0=[]
        self.throughputstamp_1=[]
        self.output_0_list=[]
        self.output_0_time=[]
        self.output_1_list=[]
        self.output_1_time=[]
        self.output_0_now=0
        self.output_1_now=0
        self.time_throughput_0=[]
        self.time_throughput_1=[]
        self.tp_int_0=0
        self.tp_int_1=0

        #initialise each bottleneck to produce different products at the beginning
        if self.label=='Bottle_Neck_C':
            self.starter_index=0
            self.qidx=0
            self.midx=0
        elif self.label=='Bottle_Neck_D':
            self.starter_index=1
            self.qidx=1
            self.midx=1

    #set the sequence of the machine, specify its upstream and downstream machine
    #MUST USE "None" if there is NO upstream/downstream machine
    def parameters(self,product_label_list,upstream_list,downstream_list,\
    process_time_mean_list,initial_queue,tables):
        self.product_label_list=product_label_list
        self.upstream_list=upstream_list
        self.downstream_list=downstream_list
        self.process_time_mean_list=process_time_mean_list
        self.process_time_list=self.process_time_mean_list
        self.queue=initial_queue
        self.output=[0 for i in range(len(product_label_list))]
        self.queuestamp_0=[]
        self.queuestamp_1=[]
        self.tables=tables


    #For a shared machine, it is necessary to choice which product to be processed
    def selection(self):
        #Choose the candidate product
        self.candidate=[]
        #Candidate generated from those whose stock is not 0
        for i in range(len(self.queue)):
            if self.queue[i] >0:
                self.candidate.append(i)

        #If all stock are empty, hold for feeding
        if self.candidate==[]:
            print(self.label,'stopped due to lack of stock at time:',self.env.now)
            yield self.sufficient_stock
            print(self.label,'received product from upstream machine at time:', self.env.now, 'production restart')
            #Once received the product from upstream, restart production
            self.sufficient_stock=self.env.event()
            self.restart_settings()

        else:
            self.pick_one()
            self.product_label=self.product_label_list[self.qidx]
            self.upstream=self.upstream_list[self.qidx]
            if self.upstream==None:
                self.upstream_exists=False
            else:
                self.upstream_exists=True
            self.downstream=self.downstream_list[self.midx]
            if self.downstream==None:
                self.downstream_exists=False
            else:
                self.downstream_exists=True

            #for testing purposes, using fixed process times
            self.process_time=self.process_time_mean_list[self.qidx]
            #in study, use normal distribution
            #self.process_time=abs(numpy.random.normal(self.process_time_mean_list[self.qidx]))

    #Same as the setting function
    def restart_settings(self):
        self.candidate=[]
        for i in range(len(self.queue)):
            if self.queue[i] !=0:
                self.candidate.append(i)
        self.pick_one()
        self.product_label=self.product_label_list[self.qidx]
        self.upstream=self.upstream_list[self.qidx]
        if self.upstream==None:
            self.upstream_exists=False
        else:
            self.upstream_exists=True
        self.downstream=self.downstream_list[self.midx]
        if self.downstream==None:
            self.downstream_exists=False
        else:
            self.downstream_exists=True
        self.process_time=self.process_time_list[self.qidx]

    def pick_one(self):

        if self.production_counter==[0,0]:
            if self.label=='Bottle_Neck_C':
                print('production plan exhausted',self.production_counter,'new production plan',self.production_plan)

            self.production_counter[0]=self.production_plan[0]
            self.production_counter[1]=self.production_plan[1]
            self.qidx=self.starter_index
            self.production_counter[self.qidx]-=1

        elif self.production_counter[self.starter_index%2]==0:
            self.qidx=(self.starter_index+1)%2
            self.production_counter[self.qidx]-=1

        else:
            self.qidx=self.starter_index
            self.production_counter[self.qidx]-=1

        #check for sufficient stock
        if (self.queue[self.starter_index]<1 and self.qidx==self.starter_index) or (self.queue[(self.starter_index+1)%2]<1 and self.qidx==(self.starter_index+1)%2):
            self.qidx=(self.qidx+1)%2
            self.production_counter[0]=self.production_plan[0]
            self.production_counter[1]=self.production_plan[1]

        #assign downstream machines
        if self.qidx==1:
            self.midx=1

        elif self.qidx==0 and self.downstream_list[0].queue[0]<self.downstream_list[2].queue[0]:
            self.midx=0

        else:
            self.midx=2


    #The main, and the only process function that needs to be added to env.process() method as the argument
    def production(self):
        while True>0:
            yield self.env.process(self.selection())
            #The production process
            yield self.env.timeout(self.process_time)
            self.data()

            #execute this part if there is a downstream machine
            if self.downstream_exists:
                self.downstream.queue[self.qidx] += 1
                if self.downstream.sufficient_stock.triggered==False:
                    self.downstream.sufficient_stock.succeed()

            #Execute this part if it has an upstream machine
            if self.upstream_exists:
                self.queue[self.qidx] -= 1
                #Examine whether there's enough stock
                if self.queue[self.qidx]<1:
                    print('----------------------------------------')
                    self.sufficient_stock=self.env.event()
                    if self.upstream.feed.triggered==False:
                        self.upstream.feed.succeed()
                    print(self.label,'run out of stock of',self.product_label,'at time:',self.env.now)
                    #Proceed only if the sufficient_stock event is triggered
                    print('----------------------------------------')

            #Examine the cumulated production time
            if self.cumulated_running_time >= self.mtbf:
                yield self.env.process(self.breakdown())
            #Examine whether the scheduled shutdown is triggered
            if self.shutdown_event.triggered==True:
                yield self.env.process(self.shutdown())

            #Proceed only if the self.working_event is triggered
            yield self.working_event

    def breakdown(self):
        self.working_event=self.env.event()
        self.bkd+=1
        print('********************************************')
        print("EMERGENCY!",self.label, "breakdown at time", self.env.now)
        self.cumulated_running_time=0
        #The restoration time needed to fix machine
        yield self.env.timeout(self.mttr)
        self.bkd_time+=self.mttr
        self.working_event.succeed()
        print(self.label,'restored, restart production at time',self.env.now)
        print('********************************************')

    def shutdown(self):
        self.working_event=self.env.event()
        print("Scheduled shutdown", self.label, "at time", self.env.now)

        #Deliver the scheduled shutdown
        yield self.env.timeout(self.shutdown_time)
        self.working_event.succeed()
        print('Scheduled shutdown finished, restart production at time',self.env.now)

    def data(self):
        self.cumulated_running_time += self.process_time
        self.total_running_time += self.process_time
        self.utilization=(self.env.now-self.bkd_time)/self.env.now
        self.throughput=[self.output[i]/self.env.now for i in range(2)]
        self.output[self.qidx] +=1
        self.expected_throughput_0=(1/self.process_time_mean_list[0])
        self.expected_throughput_1=(1/self.process_time_mean_list[1])
        if self.qidx==0:
            self.output_0+=1
            self.output_0_list.append(self.output_0)
            self.output_0_time.append(self.env.now)
            if self.output_0==30:
                self.cutoff_0=True
            self.throughput_0_std_counter.append(1/self.process_time)
            if self.cutoff_0==True:
                del self.throughput_0_std_counter[0]
            self.expected_throughput_std_0=numpy.std(self.throughput_0_std_counter)
            if self.env.now%50==0:
                output_0=self.output_0-self.output_0_now
                self.tp_int_0=output_0/50
                self.output_0_now=self.output_0
            self.throughputstamp_0.append(self.tp_int_0)
            self.time_throughput_0.append(self.env.now)
        else:
            self.output_1+=1
            self.output_1_list.append(self.output_1)
            self.output_1_time.append(self.env.now)
            if self.output_1==30:
                self.cutoff_1=True
            self.throughput_1_std_counter.append(1/self.process_time)
            if self.cutoff_1==True:
                del self.throughput_1_std_counter[0]
            self.expected_throughput_std_1=numpy.std(self.throughput_1_std_counter)
            if self.env.now%50==0:
                output_1=self.output_1-self.output_1_now
                self.tp_int_1=output_1/50
                self.output_1_now=self.output_1
            self.throughputstamp_1.append(self.tp_int_1)
            self.time_throughput_1.append(self.env.now)

    def performance_tracking(self):
        while True:
            self.timestamp.append(self.env.now+1)
            self.queuestamp_0.append(self.queue[0])
            self.queuestamp_1.append(self.queue[1])
            throughput_0=1/self.process_time_mean_list[0]
            throughput_1=1/self.process_time_mean_list[1]

            yield self.env.timeout(1)


    def slowdown(self,new_process_time_0,new_process_time_1,activation_time):
        while True:
            yield self.env.timeout(1)
            if self.env.now == activation_time:
                self.process_time_mean_list=[new_process_time_0,new_process_time_1]
                self.process_time_list=self.process_time_mean_list
                print(self.label,'changed process time to',self.process_time_mean_list, '*****************************')
                self.expected_throughput_0=1/self.process_time_mean_list[0]
                self.expected_throughput_1=1/self.process_time_mean_list[1]

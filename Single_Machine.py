import simpy
import random
import numpy
import math

class single_machine:
    def __init__(self,env,process_time_mean,initial_queue,MTBF,MTTR,label,product_label,product_index):
        #create variables bound to instance
        CreatVariable=locals()
        #initializing production setting
        print(label,'Process Time: %r'%process_time_mean,"\n","Failure rate information:",'MTBF: %r'%MTBF,'/','MTTR: %r'%MTTR)
        print('------------------------')
        self.env = env
        self.process_time_mean = process_time_mean
        self.mtbf = MTBF
        self.mttr = MTTR
        self.label = label
        self.product_label=product_label
        self.product_index=product_index

        #Initialize the possible events during production
        self.feed=self.env.event()
        self.sufficient_stock=self.env.event()
        self.working_event=self.env.event()
        self.shutdown_event=self.env.event()

        #Initialize the events'states
        self.sufficient_stock.succeed()
        self.working_event.succeed()

        #Initialize the data
        self.queue = [0,0]
        self.queue[self.product_index]=initial_queue
        self.timestamp=[self.env.now]
        self.queuestamp_0=[self.queue[0]]
        self.queuestamp_1=[self.queue[1]]
        self.throughputstamp=[]
        self.time_throughput=[]
        self.output_list=[]
        self.output_time=[]
        self.output=0
        self.starve=0
        self.starve_time=0
        self.bkd=0
        self.bkd_time=0
        self.shd=0
        self.cumulated_shutdown_time=0
        self.time_record=[]
        self.queue_record=[]
        self.throughput_record=[]
        self.utilization_record=[]
        self.upstream_list=[]

        #Initialize the control parameters
        self.cumulated_running_time = 0
        self.pt_list=[]
        self.throughput_list=[]
        self.cutoff=False
        self.expected_pt=1
        self.expected_pt_std=0
        self.expected_throughput=1
        self.expected_throughput_std=0
        self.throughput=0.5
        self.mportion=0.5
        self.midx=0
        self.m=0

    #set the sequence of the machine, specify its upstream and downstream machine, use "None" if there is NO upstream/downstream machine
    def sequence(self,upstream_list,downstream_list,tables):
        self.upstream_list=upstream_list
        self.downstream_list=downstream_list
        self.tables=tables
        if self.upstream_list==None:
            self.upstream_exists=False
        else:
            self.upstream_exists=True
        if self.downstream_list==None:
            self.downstream_exists=False
        else:
            self.downstream_exists=True

    #The main, and the only process function that needs to be called in env.process()
    def production(self):
        while True:
            #The production process
            self.process_time=self.process_time_mean #abs(numpy.random.normal(self.process_time_mean)) #
            yield self.env.timeout(self.process_time)
            self.data()

            #execute this part if there is a downstream machine
            if self.downstream_exists and len(self.downstream_list)!=1:
                self.pick_one()
                self.downstream=self.downstream_list[self.midx]
                self.downstream.queue[self.product_index] += 1
                if self.downstream.sufficient_stock.triggered==False:
                    self.downstream.sufficient_stock.succeed()

            if self.downstream_exists and len(self.downstream_list)==1:
                self.downstream=self.downstream_list[0]
                self.downstream.queue[self.product_index] += 1
                if self.downstream.sufficient_stock.triggered==False:
                    self.downstream.sufficient_stock.succeed()

            #Execute this part if it has an upstream machine
            if self.upstream_exists:
                self.queue[self.product_index] -= 1
                #Examine whether there's enough stock
                if self.queue[self.product_index]<1:
                    print('----------------------------------------')
                    self.starve +=1
                    t=self.env.now
                    self.sufficient_stock=self.env.event()
                    print(self.label,'run out of stock of',self.product_label,'at time:',self.env.now)
                    #Proceed only if the sufficient_stock event is triggered/replenished
                    yield self.sufficient_stock
                    self.starve_time+=(self.env.now-t)
                    print(self.label,'received product from upstream machine at time:', self.env.now,'production restart')
                    print('----------------------------------------')

            #Examine the cumulated production time, if reached the MTTF, trigger breakdown
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
        self.expected_throughput=0.0001
        yield self.env.timeout(self.mttr)
        self.bkd_time+=self.mttr
        print(self.label,'restored, restart production at time',self.env.now)
        self.working_event.succeed()
        print('********************************************')

    def shutdown(self):

        start=self.env.now
        self.working_event=self.env.event()
        self.shutdown_ended_event=self.env.event()
        print(self.label, "scheduled shutdown at time", self.env.now)
        self.throughput=0

        yield self.shutdown_ended_event

        #restart the production and deactivate shutdown command
        self.working_event.succeed()
        self.shutdown_event=self.env.event()
        self.shutdown_ended_event=self.env.event()

        #update the data related to shutdown
        now=self.env.now
        self.cumulated_shutdown_time+=(now-start)
        self.shd+=1
        self.throughput=numpy.mean(self.throughput_list)
        print(self.label,'scheduled shutdown finished, restart production at time',self.env.now)


    def pick_one(self):
        if self.downstream_list[0].queue[self.product_index]==self.downstream_list[1].queue[self.product_index]:
            self.midx=numpy.random.randint(2)
        elif self.downstream_list[0].queue[self.product_index]>self.downstream_list[1].queue[self.product_index]:
            self.midx=1
        else:
            self.midx=0


    def data(self):
        self.cumulated_running_time += self.process_time
        self.output += 1
        self.output_list.append(self.output)
        self.output_time.append(self.env.now)
        if self.output==10:
            self.cutoff=True
        self.pt_list.append(self.process_time)
        self.throughput_list.append(1/self.process_time)
        if self.cutoff:
            del self.pt_list[0]
            del self.throughput_list[0]
        self.expected_pt=numpy.mean(self.pt_list)
        self.expected_throughput=numpy.mean(self.throughput_list)
        self.expected_pt_std=numpy.std(self.pt_list)
        self.expected_throughput_std=numpy.std(self.throughput_list)
        self.throughput=numpy.mean(self.throughput_list)
        self.utilization=(self.env.now-self.cumulated_shutdown_time-self.bkd_time-self.starve_time)/(self.env.now-self.cumulated_shutdown_time)
        self.time_record.append(self.env.now)
        self.queue_record.append(self.queue[self.product_index])
        self.throughput_record.append(self.throughput)
        self.utilization_record.append(self.utilization)

    def performance_tracking(self):
        output_now=0
        while True:
            self.timestamp.append(self.env.now+1)
            self.queuestamp_0.append(self.queue[0])
            self.queuestamp_1.append(self.queue[1])
            if self.env.now%250==0:
                output=self.output-output_now
                throughput=output/250
                output_now=self.output
            self.throughputstamp.append(throughput)
            self.time_throughput.append(self.env.now)

            yield self.env.timeout(1)

    #experiment function
    def slowdown(self,new_process_time,activation_time):
        while True:
            yield self.env.timeout(1)
            if self.env.now == activation_time:
                self.process_time_mean=new_process_time
                print(self.label,'changed process time to',self.process_time_mean, '*****************************')
                while True:
                    self.pt_list.append(self.process_time)
                    self.throughput_list.append(1/self.process_time)
                    del self.pt_list[0]
                    del self.throughput_list[0]
                    self.expected_pt=numpy.mean(self.pt_list)
                    self.expected_throughput=numpy.mean(self.throughput_list)
                    self.expected_pt_std=numpy.std(self.pt_list)
                    self.expected_throughput_std=numpy.std(self.throughput_list)
                    self.throughput=numpy.mean(self.throughput_list)
                    yield self.env.timeout(1)

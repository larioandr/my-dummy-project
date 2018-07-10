simple Txc 
{
    parameters:
        @signal[arrival](type="long");
        @statistic[hopCount](title="hop count"; source="arrival"; record=vector,stats,timeavg,min,max,avg; interpolationmode=none);
        @display("i=block/routing");  // add a default icon
    gates:
        inout gate[];
}


network TutorialNetwork
{
    parameters:
        @figure[description](type=text; pos=5,20; font=,,bold;
            text="Random routing example - displaying last hop count");
        @figure[lasthopcount](type=text; pos=5,35; text="last hopCount: N/A");
    types:
        channel Channel extends ned.DelayChannel {
            delay = 100ms;
        }
    submodules:
        tic[6]: Txc;
    connections:
        tic[0].gate++ <--> Channel <--> tic[1].gate++;
        tic[1].gate++ <--> Channel <--> tic[2].gate++;
        tic[1].gate++ <--> Channel <--> tic[4].gate++;
        tic[3].gate++ <--> Channel <--> tic[4].gate++;
        tic[4].gate++ <--> Channel <--> tic[5].gate++;
}


network WheelNetwork
{
    parameters:
        int size;
    types:
        channel Channel extends ned.DelayChannel {
            delay = 5ms;
        }
    submodules:
        tic[size + 1]: Txc;
    connections:
        for i=1..size {
            tic[0].gate++ <--> Channel <--> tic[i].gate++;
            tic[i].gate++ <--> Channel <--> tic[i-1].gate++;
        }
}

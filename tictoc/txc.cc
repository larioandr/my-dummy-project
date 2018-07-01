#include <string.h>
#include <omnetpp.h>

using namespace omnetpp;

/**
 * Tic module will generate messages and send them to Toc, which will
 * process or lose them.
 */
class Tic : public cSimpleModule
{
public:
    Tic();
    virtual ~Tic();
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
private:
    int counter;  // Note the counter here
    simtime_t  timeout;  // wait reply timeout duration
    cMessage *timeoutEvent;  // wait reply timeout event
};

// The module class needs to be registered with OMNeT++
Define_Module(Tic);

Tic::Tic()
{
    // Set the pointer to nullptr, so that the destructor won't crash
    // even if initialize() doesn't get called because of a runtime
    // error or user cancellation during the startup process.
    timeoutEvent = nullptr;
}

Tic::~Tic()
{
    // Dispose of dynamically allocated objects
    cancelAndDelete(timeoutEvent);
}

void Tic::initialize()
{
    // Initialize counter. We'll decrement it every time and stop generation
    // when it reaches zero.
    counter = par("limit");
    WATCH(counter);

    // Create the event object we'll use for timeout modeling.
    timeoutEvent = new cMessage("timeoutEvent");

    // Generate and send initial message
    EV << "Scheduling first send to t=5.0s\n";
    cMessage *msg = new cMessage("tictocMsg");
    send(msg, "out");
    counter--;

    // Set wait timeout
    timeout = par("timeout");
    scheduleAt(simTime() + timeout, timeoutEvent);
}

void Tic::handleMessage(cMessage *msg)
{
    if (msg == timeoutEvent) {
        // If we receive the timeout event, that means the packet hasn't
        // arrived in time and we have to re-send it.
        EV << "Timeout expired, resending message and restarting timer\n";
    }
    else { // message arrived
        // Acknowledgement received -- delete the received message and cancel
        // the timeout event
        EV << "Timer cancelled\n";
        cancelEvent(timeoutEvent);
        delete msg;
    }

    // Building new message, sending it and re-setting timeout event.
    if (counter > 0) {
        cMessage *newMsg = new cMessage("tictocMsg");
        send(newMsg, "out");
        scheduleAt(simTime() + timeout, timeoutEvent);
        counter--;
    }
    else { // counter reached zero
        EV << "Counter reached zero.\n";
    }
}

/**
 * Sends back and acknowledgement -- or not.
 */
class Toc : public cSimpleModule {
  public:
    Toc();
    virtual ~Toc();
  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
  private:
    cMessage *delayEvent;  // a processing delay timer
    cMessage *tictocMsg;  // a cached request
    double loseProb;  // probability to `lose' a message
};

Define_Module(Toc);

Toc::Toc()
{
    delayEvent = tictocMsg = nullptr;
}

Toc::~Toc()
{
    delete tictocMsg;
    cancelAndDelete(delayEvent);
}

void Toc::initialize()
{
    // Reading NED parameters
    loseProb = par("loseProb");

    // Initializing events and message cache
    delayEvent = new cMessage("delayEvent");
    tictocMsg = nullptr;
}

void Toc::handleMessage(cMessage *msg)
{
    if (msg == delayEvent) {
        // If processing finished, send the message back.
        EV << "Sending back the same message as acknowledgement.\n";
        send(tictocMsg, "out");
        tictocMsg = nullptr;
    }
    else {  // message from Tic arrived 
        if (tictocMsg != nullptr) {
            EV << "Dropping message - Toc is busy\n";
            delete msg;
        }
        else { // Toc is not busy
            if (uniform(0, 1) < loseProb) {
                EV << "\"Losing\" message.\n";
                bubble("message lost");
                delete msg;
            }
            else {  // received successfully
                simtime_t delay = par("delayTime");
                EV << "Wait before sending back for " << delay << " secs...\n";
                scheduleAt(simTime() + delay, delayEvent);
                tictocMsg = msg;
            }
        }
    }
}


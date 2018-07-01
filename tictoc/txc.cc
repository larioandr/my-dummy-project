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
    cMessage *message;  // a message we are currently transmitting
    int seq;  // message sequence number

    cMessage *generateNewMessage();
    void sendCopyOf(cMessage *msg);
    bool checkMessagesLimit() const;
};

// The module class needs to be registered with OMNeT++
Define_Module(Tic);

Tic::Tic()
{
    // Set the pointer to nullptr, so that the destructor won't crash
    // even if initialize() doesn't get called because of a runtime
    // error or user cancellation during the startup process.
    timeoutEvent = message = nullptr;
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

    // Initialize the sequence number
    seq = 0;

    // Create the event object we'll use for timeout modeling.
    timeoutEvent = new cMessage("timeoutEvent");

    if (checkMessagesLimit()) {
        // Generate and send initial message
        message = generateNewMessage();
        sendCopyOf(message);

        // Set wait timeout
        timeout = par("timeout");
        scheduleAt(simTime() + timeout, timeoutEvent);

        // Update the counter
        counter--;
    }

}

void Tic::handleMessage(cMessage *msg)
{
    if (msg == timeoutEvent) {
        // If we receive the timeout event, that means the packet hasn't
        // arrived in time and we have to re-send it.
        EV << "Timeout expired, resending message and restarting timer\n";
        sendCopyOf(message);
        scheduleAt(simTime() + timeout, timeoutEvent);
    }
    else { // message arrived
        // Acknowledgement received!
        EV << "Received: " << msg->getName() << "\n";
        delete msg;

        // Also delete the stored message and cancel timeout event.
        EV << "Timer cancelled.\n";
        delete message;
        cancelEvent(timeoutEvent);

        // Ready to send another one.
        if (checkMessagesLimit()) {
            message = generateNewMessage();
            EV << "Sending new message " << message->getName() << "\n";
            sendCopyOf(message);
            scheduleAt(simTime() + timeout, timeoutEvent);

            // Update the counter
            counter--;
        }
    }
}

cMessage *Tic::generateNewMessage()
{
    // Generate a message with a different name every time.
    char msgname[20];
    sprintf(msgname, "tic-%d", ++seq);
    cMessage *msg = new cMessage(msgname);
    return msg;
}

void Tic::sendCopyOf(cMessage *msg)
{
    // Duplicate the message and send the copy.
    cMessage *copy = (cMessage *)msg->dup();
    send(copy, "out");
}

bool Tic::checkMessagesLimit() const
{
    return counter > 0;
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


#include <string.h>
#include <omnetpp.h>

using namespace omnetpp;

class Txc : public cSimpleModule {
  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void forwardMessage(cMessage *msg);
    virtual cMessage *generateMessage();
};

Define_Module(Txc);

void Txc::initialize()
{
    // Module 0 sends the first message
    if (getIndex() == 0) {
        // Boot the process scheduling the initial message as a self-message
        cMessage *msg = generateMessage();
        EV << "built initial message `" << msg->getName() << "'\n";
        forwardMessage(msg);
    }
}

void Txc::handleMessage(cMessage *msg)
{
    if (getIndex() == 3) {
        EV << "reached Tic[3], delete message\n";
        delete msg;
    } else {
        forwardMessage(msg);
    }
}

void Txc::forwardMessage(cMessage *msg)
{
    // In this example we just pick a random gate to send msg on.
    // We draw a random number between 0 and the size of gate `out[]'.
    int n = gateSize("out");
    int k = intuniform(0, n-1);

    EV << "Forwarding message " << msg << " on port out[" << k << "]\n";
    send(msg, "out", k);
}

cMessage *Txc::generateMessage()
{
    return new cMessage("tictocMsg");
}

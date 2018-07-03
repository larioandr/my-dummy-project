#include <string.h>
#include <omnetpp.h>
#include "tictoc_m.h"

using namespace omnetpp;

class Txc : public cSimpleModule {
  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

    virtual void refreshDisplay() const override;

    virtual TicTocMsg *generateMessage();
    virtual void forwardMessage(TicTocMsg *msg);
  private:
    long numSent;
    long numReceived;
    cHistogram hopCountStats;
    cOutVector hopCountVector;
};

Define_Module(Txc);

void Txc::initialize()
{
    numSent = 0;
    WATCH(numSent);

    numReceived = 0;
    WATCH(numReceived);

    hopCountStats.setName("hopCountStats");
    hopCountStats.setRange(0, NAN);
    hopCountStats.setNumPrecollectedValues(10);
    hopCountStats.setRangeExtensionFactor(1.5);
    hopCountVector.setName("HopCount");

    // Module 0 sends the first message
    if (getIndex() == 0) {
        // Boot the process scheduling the initial message as a self-message
        EV << "Generating initial message: ";
        TicTocMsg *msg = generateMessage();
        EV << msg << endl;
        forwardMessage(msg);
        numSent++;
    }
}

void Txc::handleMessage(cMessage *msg)
{
    TicTocMsg *ttmsg = check_and_cast<TicTocMsg*>(msg);

    if (ttmsg->getDestination() == getIndex()) {
        // Message arrived at its destination.
        int hopcount = ttmsg->getHopCount();
        EV << "Message " << ttmsg << " arrived after " << hopcount << " hops.\n";
        bubble("ARRIVED, starting new one!");

        // Update statistics.
        numReceived++;
        hopCountVector.record(hopcount);
        hopCountStats.collect(hopcount);

        // Destroy the delivered message.
        delete ttmsg;

        // Generate another one
        EV << "Generating another message: ";
        TicTocMsg *newmsg = generateMessage();
        EV << newmsg << endl;
        forwardMessage(newmsg);
        numSent++;
    } else {
        // We are not the destination, just forward the message.
        forwardMessage(ttmsg);
    }
}

void Txc::forwardMessage(TicTocMsg *msg)
{
    // Increment hop count.
    msg->setHopCount(msg->getHopCount() + 1);

    // In this example we just pick a random gate to send msg on.
    // We draw a random number between 0 and the size of gate `gate[]'.
    int n = gateSize("gate");
    int k;

    if (msg->getArrivalGate() && gateSize("gate") > 1) {
        k = intuniform(0, n-2);
        k = k < msg->getArrivalGate()->getIndex() ? k : k + 1;
    } else {
        k = intuniform(0, n-1);
    }

    EV << "Forwarding message " << msg << " on port gate[" << k << "]\n";
    send(msg, "gate$o", k);
}

TicTocMsg *Txc::generateMessage()
{
    // Produce source and destination addresses.
    int src = getIndex();  // our module index
    int n = getVectorSize();  // module vector size
    int dest = intuniform(0, n-2);
    if (dest >= src) {
        dest++;
    }

    char msgname[20];
    sprintf(msgname, "tic-%d-%d", src, dest);

    TicTocMsg *msg = new TicTocMsg(msgname);
    msg->setSource(src);
    msg->setDestination(dest);
    return msg;
}

void Txc::refreshDisplay() const
{
    char buf[40];
    sprintf(buf, "rcvd: %ld sent: %ld", numReceived, numSent);
    getDisplayString().setTagArg("t", 0, buf);
}

void Txc::finish()
{
    EV << "Sent:              " << numSent << endl;
    EV << "Received:          " << numReceived << endl;
    EV << "Hop count, min:    " << hopCountStats.getMin() << endl;
    EV << "Hop count, max:    " << hopCountStats.getMax() << endl;
    EV << "Hop count, mean:   " << hopCountStats.getMean() << endl;
    EV << "Hop count, stddev: " << hopCountStats.getStddev() << endl;

    recordScalar("#sent", numSent);
    recordScalar("#received", numReceived);

    hopCountStats.recordAs("hop count");
}

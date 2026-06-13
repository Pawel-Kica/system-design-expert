## What It Is

The CAP Theorem (Brewer's Theorem) states that in a distributed system, when a **network partition** occurs, you must choose between **Consistency** and **Availability**. You cannot have both at the same time during a partition.

## The Three Properties

**Consistency (C)** means every node in the system returns the same, most recent data. If a user deposits 1000 USDT via Node A, then Node B must also reflect that deposit before responding to any query. If it can't confirm it has the latest data, it refuses to answer.

**Availability (A)** means every request receives a response, the system never says "sorry, come back later." It will always answer, even if the data might be slightly outdated.

**Partition Tolerance (P)** means the system continues to function even when network communication between nodes is lost. This is not a choice, partitions **will** happen in any distributed system (cables break, switches fail, datacenters lose connectivity). P is a fact of life, not an option.

## The Real Decision

The classic "pick 2 of 3" framing is misleading. In practice, since partition tolerance is mandatory (you can't prevent network failures), the real question is:

> **When a partition occurs, do you choose Consistency or Availability?**

- **CP (Consistency + Partition Tolerance):** The system refuses to serve requests it can't guarantee are correct. Users may see downtime, but data integrity is preserved.
- **AP (Availability + Partition Tolerance):** The system always responds, but some responses may be based on stale data. Users always get an answer, but it might not reflect the latest state.

When there is **no partition** (everything is healthy), you can have both consistency and availability simultaneously. The trade-off only kicks in during failure.

## How to Decide: Think About Consequences

The right choice depends entirely on **what happens to the user when you choose wrong**. Ask yourself two questions:

1. What's the consequence of showing stale/incorrect data? (cost of losing consistency)
2. What's the consequence of the system being unavailable? (cost of losing availability)

Whichever consequence is worse tells you what to prioritize.

## Examples

### CP Systems (Consistency wins)

**Banking / financial transactions**. If Node B doesn't know about a withdrawal processed by Node A, it might allow a second withdrawal, creating money from nothing. Showing "temporarily unavailable" is far better than processing transactions on incorrect balances. The derivatives trading platform is a textbook CP case: wrong margin data can lead to unauthorized position openings and real financial losses.

**Airline seat reservations**. Two people in different regions try to book the same last seat. If both succeed on stale data, you have an oversold flight and a furious customer at the gate. Better to briefly pause reservations than sell a seat twice.

### AP Systems (Availability wins)

**Social media feeds (Twitter/X, Instagram)**. If a user sees a post from 3 seconds ago instead of 1 second ago, nobody notices or cares. But if the feed won't load at all, users leave for a competitor. Stale data is a non-issue; downtime is a disaster.

**Live viewer counts (Twitch, YouTube)**. Whether the counter shows 3,000 or 3,001 viewers is irrelevant. The number just needs to be "roughly right." Refusing to show a count because you can't guarantee exactness would be absurd.

**News sites (NYT, CNN)**. During a partition, serving articles from 5 minutes ago is perfectly fine. Users came to read news, they don't need the absolute latest millisecond of updates. An unavailable homepage, on the other hand, is a total failure.

**Chat applications (Slack, Discord, WhatsApp)**. Users need to keep messaging. If messages appear briefly out of order during a partition, that's a minor inconvenience easily fixed after recovery. A chat app that says "you can't send messages right now" feels broken and users will switch to a competitor.

## Key Takeaway

CAP is not about memorizing definitions. It's about **trade-off reasoning**: given this specific system and its business context, what failure mode is more acceptable? That reasoning, not the acronym, is what matters in system design.

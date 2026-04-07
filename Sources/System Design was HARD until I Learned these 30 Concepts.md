Source: [YouTube](https://www.youtube.com/watch?v=s9Qh9fWeOAk)
Transcribed: 2026-04-04

---

If you want to level up from a junior developer to a senior engineer or land a high-paying job at a big tech company, you need to learn system design. But where do you start?

To master system design, you first need to understand the core concepts and fundamental building blocks that come up when designing real-world systems or tackling system design interview questions.

In this video, I will break down the 30 most important system design concepts you need to know. Learning these concepts helped me land high-paying offers from multiple big tech companies and within my 8 years as a software engineer, I've seen them used repeatedly when building and scaling large-scale systems.

Let's get started.

## 1. Client-Server Architecture

Almost every web application that you use is built on this simple yet powerful concept called client-server architecture. Here is how it works. On one side, you have a **client**. This could be a web browser, a mobile app, or any other frontend application. And on the other side, you have a **server**, a machine that runs continuously, waiting to handle incoming requests.

The client sends a request to store, retrieve, or modify data. The server receives the request, processes it, performs the necessary operations, and sends back a response. This sounds simple, right? But there is a big question: how does the client even know where to find a server?

## 2. IP Addresses & DNS

A client doesn't magically know where a server is. It needs an address to locate and communicate with it. On the internet, computers identify each other using **IP addresses**, which work like phone numbers for servers. Every publicly deployed server has a unique IP address.

When a client wants to interact with a service, it must send requests to the correct IP address. But there is a problem. When we visit a website, we don't type its IP address, we just enter the website name, right? Instead of relying on hard-to-remember IP addresses, we use something much more human-friendly: **domain names**. But we need a way to map a domain name to its corresponding IP address.

This is where **DNS** (Domain Name System) comes in. It maps easy-to-remember domain names like algomaster.io to their corresponding IP addresses. When you type algomaster.io into your browser, your computer asks a DNS server for the corresponding IP address. Once the DNS server responds with the IP, your browser uses it to establish a connection with the server and make a request.

You can find the IP address of any domain name using the `ping` command.

## 3. Proxy & Reverse Proxy

When you visit a website, your request doesn't always go directly to the server. Sometimes it passes through a proxy or reverse proxy first.

A **proxy server** acts as a middleman between your device and the internet. When you request a webpage, the proxy forwards your request to the target server, retrieves the response, and sends it back to you. A proxy server hides your IP address, keeping your location and identity private.

A **reverse proxy** works the other way around. It intercepts the client request and forwards them to the backend server based on predefined rules.

## 4. Latency

Whenever a client communicates with a server, there is always some delay. One of the biggest causes of this delay is physical distance. For example, if our server is in New York, but a user in India sends a request, the data has to travel halfway across the world, and then the response has to make the same long trip back. This round-trip delay is called **latency**. High latency can make applications feel slow and unresponsive.

One way to reduce latency is by deploying our service across multiple data centers worldwide. This way, users can connect to the nearest server instead of waiting for data to travel across the globe.

## 5. HTTP & HTTPS

Once a connection is made, how do clients and servers actually communicate? Every time you visit a website, your browser and the server communicate using a set of rules called **HTTP**. That's why most URLs start with HTTP or its secure version HTTPS.

The client sends a request to the server. This request includes a **header** containing details like the request type, browser type, and cookies, and sometimes a **request body**, which carries additional data like form inputs. The server processes the request and responds with an HTTP response, either returning the requested data or an error message if something goes wrong.

HTTP has a major security flaw. It sends data in plain text. Modern websites use **HTTPS**. HTTPS encrypts all data using SSL or TLS protocol, ensuring that even if someone intercepts the request, they can't read or alter it.

## 6. APIs (Application Programming Interfaces)

But clients and servers don't directly exchange raw HTTP requests and responses. HTTP is just a protocol for transferring data, but it doesn't define how requests should be structured, what format responses should be in, or how different clients should interact with a server.

This is where **APIs** (Application Programming Interfaces) come in. Think of an API as a middleman that allows clients to communicate with servers without worrying about low-level details.

A client sends a request to an API. The API hosted on a server processes the request, interacts with databases or other services, and prepares a response. The API sends back the response in a structured format, usually JSON or XML, which the client understands and can display. There are different API styles to serve different needs. Two of the most popular ones are REST and GraphQL.

## 7. REST API

Among the different API styles, REST is the most widely used. A **REST API** follows a set of rules that defines how clients and servers communicate over HTTP in a structured way.

- REST is **stateless**. Every request is independent.
- Everything is treated as a **resource** (e.g., users, orders, products).
- It uses standard HTTP methods: **GET** to retrieve data, **POST** to create new data, **PUT** to update existing data, and **DELETE** to remove data.

REST APIs are great because they are simple, scalable, and easy to cache. But they have limitations, especially when dealing with complex data retrieval. REST endpoints often return more data than needed, leading to inefficient network usage.

## 8. GraphQL

To address these challenges, **GraphQL** was introduced in 2015 by Facebook. Unlike REST, GraphQL lets clients ask for exactly what they need. Nothing more, nothing less.

With a REST API, if you need a user's profile along with recent posts, you might have to make multiple requests to different endpoints. With GraphQL, you can combine those requests into one and fetch exactly the data you need in a single query. The server responds with only the requested fields.

However, GraphQL also comes with trade-offs. It requires more processing on the server side, and it isn't as easy to cache as REST.

## 9. Databases (SQL vs NoSQL)

Now when a client makes a request, they usually want to store or retrieve data. But this brings up another question. Where is the actual data stored? If our application deals with small amounts of data, we could store it as a variable or as a file and load it in memory. But modern applications handle massive volumes of data, far more than what memory can efficiently handle. That's why we need a dedicated server for storing and managing data: a **database**.

A database is the backbone of any modern application. It ensures that data is stored, retrieved, and managed efficiently while keeping it secure, consistent, and durable. When a client requests to store or retrieve data, the server communicates with the database, fetches the required information, and returns it to the client.

But not all databases are the same. In system design, we typically choose between **SQL** and **NoSQL** databases.

**SQL databases** store data in tables with a strict predefined schema, and they follow ACID capabilities. Because of these guarantees, SQL databases are ideal for applications that require strong consistency and structured relationships such as banking systems.

**NoSQL databases**, on the other hand, are designed for high scalability and performance. They don't require a fixed schema, and use different data models including key-value stores, document stores, graph databases, and wide-column stores, which are optimized for large-scale distributed data.

So which one should you use?
- If you need structured relational data with strong consistency, **SQL** is the better choice.
- If you need high scalability and flexible schema, **NoSQL** is the better choice.
- Many modern applications use both SQL and NoSQL together.

## 10. Vertical Scaling

As our user base grows, so does the number of requests hitting our application servers. One of the quickest solutions is to upgrade the existing server by adding more CPU, RAM, or storage. This approach is called **vertical scaling** (or scaling up), which makes a single machine more powerful.

But there are some major limitations with this approach:
- You can't keep upgrading a server forever. Every machine has a maximum capacity.
- More powerful servers become exponentially more expensive.
- If this one server crashes, the entire system goes down.

So while vertical scaling is a quick fix, it's not a long-term solution for handling high traffic and ensuring system reliability.

## 11. Horizontal Scaling & Load Balancing

Let's look at a better approach, one that makes our system more scalable and fault-tolerant. Instead of upgrading a single server, what if we add more servers to share the load? This approach is called **horizontal scaling** (or scaling out), where we distribute the workload across multiple machines. More servers equals more capacity, which means the system can handle increasing traffic more effectively. If one server goes down, others can take over, which improves reliability.

But horizontal scaling introduces a new challenge. How do clients know which server to connect to? This is where a **load balancer** comes in. A load balancer sits between clients and backend servers, acting as a traffic manager that distributes requests across multiple servers. If one server crashes, the load balancer automatically redirects traffic to another healthy server.

But how does a load balancer decide which server should handle the next request? It uses load balancing algorithms such as **round-robin**, **least connections**, and **IP hashing**.

## 12. Database Scaling Introduction

So far we have talked about scaling our application servers. But as traffic grows, the volume of data also increases. At first, we can scale a database vertically by adding more CPU, RAM, and storage similar to application servers. But there is a limit of how much a single machine can handle. So let's explore other database scaling techniques that can help manage large volumes of data efficiently.

## 13. Database Indexing

One of the quickest and most effective ways to speed up database read queries is **indexing**. Think of it like the index page at the back of a book. Instead of flipping through every page, you jump directly to the relevant section. Database index works the same way. It's a super efficient lookup table that helps the database quickly locate the required data without scanning the entire table.

An index stores column values along with pointers to actual data rows in the table. Indexes are typically created on columns that are frequently queried, such as primary keys, foreign keys, and columns frequently used in WHERE conditions.

While indexes speed up reads, they slow down writes, since the index needs to be updated whenever data changes. That's why we should only index the most frequently accessed columns.

## 14. Database Replication

Indexing can significantly improve read performance. But what if even indexing isn't enough? And our single database server can't handle the growing number of read requests. That's where our next database scaling technique, **replication**, comes in.

Just like we added more application servers to handle increasing traffic, we can scale our database by creating copies of it across multiple servers. Here is how it works:
- We have one **primary database** (also called the primary replica) that handles all write operations.
- We have multiple **read replicas** that handle read queries.
- Whenever data is written to primary database, it gets copied to read replicas so that they stay in sync.

Replication improves the read performance since read requests are spread across multiple replicas, reducing the load on each one. This also improves availability since if the primary replica fails, a read replica can take over as the new primary.

## 15. Database Sharding

Replication is great for scaling read-heavy applications. But what about scaling write operations or storing huge amounts of data? Let's say our service became popular. It now has millions of users. And our database has grown to terabytes of data. A single database server will eventually struggle to handle all this data efficiently.

Instead of keeping everything in one place, we split the database into smaller, more manageable pieces and distribute them across multiple servers. This technique is called **sharding**. Here is how it works:
- We divide the database into smaller parts called **shards**.
- Each shard contains a subset of the total data.
- Data is distributed based on a **sharding key** (e.g., user ID).

By distributing data this way, we reduce database load (since each shard handles only a portion of queries) and speed up read and write performance (since queries are distributed across multiple shards, instead of hitting a single database).

Sharding is also referred to as **horizontal partitioning**, since it splits data by rows.

## 16. Vertical Partitioning

But what if the issue isn't the number of rows, but rather the number of columns? In such cases, we use **vertical partitioning**, where we split the database by columns.

Imagine we have a user table that stores profile details, login history, and billing information. As this table grows, queries become slower, because the table must scan many columns even when a request only needs a few specific fields.

To optimize this, we split the user table into smaller, more focused tables, based on usage patterns. This improves query performance, since each request only scans relevant columns instead of the entire table. It also reduces unnecessary disk IO, making data retrieval quicker.

## 17. Caching

However, no matter how much we optimize the database, retrieving data from disk is always slower than retrieving it from memory. What if we could store frequently accessed data in memory? This is called **caching**.

Caching is used to optimize the performance of a system by storing frequently accessed data in memory, instead of repeatedly fetching it from the database. One of the most common caching strategies is the **cache-aside pattern**. Here is how it works:
1. When a user requests data, the application first checks the cache.
2. If the data is in the cache, it's returned instantly, avoiding a database call (**cache hit**).
3. If the data is not in the cache, the application retrieves it from the database, stores it in the cache for future requests, and returns it to the user (**cache miss**).
4. Next time the same data is requested, it's served directly from cache, making the request much faster.

To prevent outdated data from being served, we use **TTL** (Time to Live) values.

## 18. Denormalization

Most relational databases use normalization to store data efficiently by breaking it into separate tables. While this reduces redundancy, it also introduces joins. When retrieving data from multiple tables, the data must combine them using join operations, which can slow down queries as the dataset grows.

**Denormalization** reduces the number of joins by combining related data into a single table, even if it means some data gets duplicated. For example, instead of keeping users and orders in a separate table, we create a user_orders table that stores user details along with their latest orders. Now, when retrieving a user's order history, we don't need a join operation. The data is already stored together, leading to faster queries and better read performance.

Denormalization is often used in read-heavy applications, where speed is more critical. But the downside is, it leads to increased storage and more complex update requests.

## 19. CAP Theorem

As we scale our system across multiple servers, databases, and data centers, we enter the world of distributed systems. One of the fundamental principles of distributed systems is the **CAP theorem**, which states that no distributed system can achieve all three of the following at the same time: **Consistency**, **Availability**, and **Partition Tolerance**.

Since network failures are inevitable, we must choose between consistency + partition tolerance or availability + partition tolerance.

## 20. Blob Storage

Most modern applications don't just store text records. They also need to handle images, videos, PDFs, and other large files. Traditional databases are not designed to store large, unstructured files efficiently. So what's the solution?

We use **blob storage** like Amazon S3. Blobs are individual files like images, videos, or documents. These blobs are stored inside logical containers or **buckets** in the cloud. Each file gets a unique URL, making it easy to retrieve and serve over the web.

Advantages: scalability, pay-as-you-go model, automatic replication, easy access. A common use case is to stream audio or video files to user applications in real time.

## 21. CDN (Content Delivery Network)

But streaming the video file directly from blob storage can be slow, especially if the data is stored in a distant location. For example, imagine you are in India trying to watch a YouTube video that's hosted on a server in California. Since the video data has to travel across the world, this could lead to buffering and slow load times.

A **CDN** (Content Delivery Network) solves this problem by delivering content faster to users based on their location. A CDN is a global network of distributed servers that work together to deliver web content like HTML pages, JavaScript files, images, and videos to users based on their geographic location. Since content is served from the closest CDN server, users experience faster load times with minimal buffering.

## 22. WebSockets

Let's move to the next system design concept, which can help us build real-time applications. Most web applications use HTTP, which follows a request-response model. The client sends a request, the server processes the request and sends a response. If the client needs new data, it must send another request. This works fine for static web pages, but it's too slow and inefficient for real-time applications, like live chat applications, stock market dashboards, or online multiplayer games.

With HTTP, the only way to get real-time updates is through frequent polling, sending repeated requests every few seconds. But polling is inefficient because it increases the server load and wastes bandwidth, and most responses are empty when there is no new data.

**WebSockets** solve this problem by allowing continuous two-way communication between the client and the server over a single persistent connection. The client initiates a WebSocket connection with the server. Once established, the connection remains open. The server can push updates to the client at any time without waiting for a request. The client can also send messages instantly to the server. This enables real-time interactions and eliminates the need for polling.

## 23. Webhooks

WebSockets enable real-time communication between a client and a server. But what if a server needs to notify another server when an event occurs? For example, when a user makes a payment, the payment gateway needs to notify your application instantly.

Instead of constantly polling an API to check if an event has occurred, **webhooks** allow a server to send an HTTP request to another server as soon as the event occurs. Here is how it works: the receiver (e.g., your app) registers a webhook URL with the provider. When an event occurs, the provider sends an HTTP POST request to the webhook URL with event details. It conserves server resources and reduces unnecessary API calls.

## 24. Microservices

Traditionally, applications were built using a **monolithic architecture**, where all features are inside one large codebase. This setup works fine for small applications, but for large-scale systems, monoliths become hard to manage, scale, and deploy.

The solution is to break down your application into smaller independent services called **microservices** that work together. Each microservice:
- Handles a single responsibility
- Has its own database and logic
- Can scale independently
- Communicates with other microservices using APIs or message queues

This way, services can be scaled and deployed individually without affecting the entire system.

## 25. Message Queues

However, when multiple microservices need to communicate, direct API calls aren't always efficient. A **message queue** enables services to communicate asynchronously, allowing requests to be processed without blocking other operations.

Here is how it works:
- A **producer** places a message in the queue.
- The queue temporarily hosts the message.
- A **consumer** retrieves the message and processes it.

Using message queues, we can decouple services, improve scalability, and prevent overload on internal services within our system.

## 26. Rate Limiting

How do we prevent overload for the public APIs and services that we deploy? For that, we use **rate limiting**. Imagine a bot starts making thousands of requests per second to your website. Without restrictions, this could crash your servers by consuming all available resources and degrade performance for legitimate users.

Rate limiting restricts the number of requests a client can send within a specific time frame. Every user or IP address is assigned a request quota (e.g., 100 requests per minute). If they exceed this limit, the server blocks additional requests temporarily and returns an error.

There are various rate limiting algorithms. Some of the popular ones are **fixed window**, **sliding window**, and **token bucket**. We don't need to implement our own rate limiting system. This can be handled by something called an API Gateway.

## 27. API Gateway

An **API Gateway** is a centralized service that handles authentication, rate limiting, logging, monitoring, request routing, and much more. Imagine a microservices-based application with multiple services.

Instead of exposing each service directly, an API Gateway acts as a **single entry point** for all client requests. It routes the request to the appropriate microservice, and the response is sent back through the gateway to the client. API Gateway simplifies API management and improves scalability and security.

## 28. Idempotency

In distributed systems, network failures and service retries are common. If a user accidentally refreshes a payment page, the system might receive two payment requests instead of one.

**Idempotency** ensures that repeated requests produce the same result, as if the request was made only once. Here is how it works:
1. Each request is assigned a unique ID.
2. Before processing, the system checks if the request has already been handled.
3. If yes, it ignores the duplicate request.
4. If no, it processes the request normally.

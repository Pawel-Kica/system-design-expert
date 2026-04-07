Source: [YouTube](https://www.youtube.com/watch?v=F2FmTdLtb_4)
Transcribed: 2026-04-05

---

This complete system design tutorial covers scalability, reliability, data handling, and high-level architecture with clear explanations, real-world examples, and practical strategies. It will teach you the core concepts you need to know for a system design interview.

The system design interview doesn't have to do much with coding. People don't want to see you write actual code, but how you glue an entire system together. And that is exactly what we're going to cover in this tutorial. We'll go through all of the concepts that you need to know to ace your job interview.

## Computer Architecture Basics

Before designing large-scale distributed systems, it's important to understand the high-level architecture of the individual computer. Let's see how different parts of the computer work together to execute our code.

Computers function through a layered system, each optimized for varying tasks. At the core, computers understand only binary, zeros and ones. These are represented as bits. One bit is the smallest data unit in computing, it can be either zero or one. One byte consists of eight bits and it's used to represent a single character like "a" or a number like 1. Expanding from here we have kilobyte, megabyte, gigabytes, and terabytes.

**Disk Storage** holds the primary data. It can be either HDD or SSD type. Disk storage is non-volatile, it maintains data without power, meaning if you turn off or restart the computer the data will still be there. It contains the OS, applications, and all user files. In terms of size, disks typically range from hundreds of gigabytes to multiple terabytes. While SSDs are more expensive, they offer significantly faster data retrieval than HDD. For instance, an SSD may have a read speed of 500 MB/s to 3500 MB/s while an HDD might offer 80 to 260 MB/s.

**RAM (Random Access Memory)** serves as the primary active data holder and it holds data structures, variables, and application data that are currently in use or being processed. When a program runs, its variables, intermediate computations, runtime stack, and more are stored in RAM because it allows for quick read and write access. This is volatile memory, meaning it requires power to retain its contents, and after you restart the computer the data may not be persisted. In terms of size, RAMs range from a few gigabytes in consumer devices to hundreds of gigabytes in high-end servers. Their read-write speed often surpasses 5000 MB/s, which is faster than even the fastest SSDs.

**Cache** is smaller than RAM, typically measured in megabytes, but access times for cache memory are even faster than RAM, often just a few nanoseconds for the L1 cache. The CPU first checks the L1 cache for the data. If it's not found, it checks the L2 and L3 cache, and then finally it checks the RAM. The purpose of a cache is to reduce the average time to access data. That's why we store frequently used data here to optimize CPU performance.

**CPU** is the brain of the computer. It fetches, decodes, and executes instructions. When you run your code, it's the CPU that processes the operations defined in that program. But before it can run our code, which is written in high-level languages like Java, C++, Python, or other languages, our code first needs to be compiled into machine code. A compiler performs this translation, and once the code is compiled into machine code, the CPU can execute it. It can read and write from our RAM, disk, and cache data.

**Motherboard (Mainboard)** is what you might think of as the component that connects everything. It provides the pathways that allow data to flow between these components.

## Production App Architecture

Now let's have a look at a very high-level architecture of a production-ready app.

**CI/CD Pipeline (Continuous Integration and Continuous Deployment)** ensures that our code goes from the repository through a series of tests and pipeline checks and onto the production server without any manual intervention. It's configured with platforms like Jenkins or GitHub Actions for automating our deployment processes.

**Load Balancers and Reverse Proxies**: Once our app is in production it has to handle lots of user requests. This is managed by our load balancers and reverse proxies like Nginx. They ensure that the user requests are evenly distributed across multiple servers, maintaining a smooth user experience even during traffic spikes.

**External Storage**: Our server is also going to need to store data. For that we also have an external storage server that is not running on the same production server, instead is connected over a network. Our servers might also be communicating with other servers as well, and we can have many such services, not just one.

**Logging and Monitoring**: To ensure everything runs smoothly we have logging and monitoring systems keeping a keen eye on every micro-interaction, storing logs and analyzing data. It's standard practice to store logs on external services, often outside of our primary production server. For the backend, tools like PM2 can be used for logging and monitoring. On the frontend, platforms like Sentry can be used to capture and report errors in real time.

**Alerting**: When things don't go as planned, meaning our logging systems detect failing requests or anomalies, first it informs our alerting service. After that, push notifications are sent to keep users informed, from generic "something went wrong" to specific "payment failed." Modern practice is to integrate these alerts directly into platforms we commonly use, like Slack. Imagine a dedicated Slack channel where alerts pop up at the moment an issue arises. This allows developers to jump into the action almost instantly, addressing the root cause before it escalates.

**Debugging Process**: After that, developers have to debug the issue.

1. **Identify the issue**: First and foremost, the issue needs to be identified. Those logs we spoke about earlier, they are our first port of call. Developers go through them searching for patterns or anomalies that could point to the source of the problem.
2. **Replicate in a safe environment**: After that it needs to be replicated in a safe environment. The golden rule is to never debug directly in the production environment. Instead, developers recreate the issue in a staging or test environment. This ensures users don't get affected by the debugging process.
3. **Debug**: Then developers use tools to peer into the running application and start debugging.
4. **Hotfix**: Once the bug is fixed, a hotfix is rolled out. This is a quick temporary fix designed to get things running again. It's like a patch before a more permanent solution can be implemented.

## Pillars of System Design

In this section, let's understand the pillars of system design and what it really takes to create a robust and resilient application.

Before we jump into the technicalities, let's talk about what actually makes a good design. When we talk about good design in system architecture, we are really focusing on a few key principles:

- **Scalability**: Can our system grow with its user base?
- **Maintainability**: Can future developers understand and improve our system?
- **Efficiency**: Are we making the best use of our resources?

But good design also means planning for failure and building a system that not only performs well when everything is running smoothly, but also maintains its composure when things go wrong.

At the heart of system design are three key elements:

- **Moving data**: Ensuring that data can flow seamlessly from one part of our system to another. Whether it's user requests hitting our servers or data transfers between databases, we need to optimize for speed and security.
- **Storing data**: This isn't just about choosing between SQL or NoSQL databases. It's about understanding access patterns, indexing strategies, and backup solutions. We need to ensure that our data is not only stored securely but is also readily available when needed.
- **Transforming data**: Taking raw data and turning it into meaningful information, whether it's aggregating log files for analysis or converting user input into a different format.

## CAP Theorem

Now let's take a moment to understand the crucial concept in system design: the CAP theorem, also known as Brewer's Theorem, named after computer scientist Eric Brewer. This theorem is a set of principles that guide us in making informed trade-offs between three key components of a distributed system: consistency, availability, and partition tolerance.

- **Consistency** ensures that all nodes in the distributed system have the same data at the same time. If you make a change to one node, that change should also be reflected across all nodes. Think of it like updating a Google Doc: if one person makes an edit, everyone else sees that edit immediately.
- **Availability** means that the system is always operational and responsive to requests, regardless of what might be happening behind the scenes. Like a reliable online store, no matter when you visit, it's always open and ready to take your order.
- **Partition Tolerance** refers to the system's ability to continue functioning even when a network partition occurs, meaning if there is a disruption in communication between nodes, the system still works. It's like having a group chat where even if one person loses connection, the rest of the group can continue chatting.

According to CAP theorem, a distributed system can only achieve two out of these three properties at the same time. If you prioritize consistency and partition tolerance, you might have to compromise on availability, and vice versa. For example, a banking system needs to be consistent and partition tolerant to ensure financial accuracy, even if it means some transactions take longer to process, temporarily compromising availability.

Every design decision comes with trade-offs. For example, a system optimized for read operations might perform poorly on write operations. Or in order to gain performance we might have to sacrifice a bit of complexity. So it's not about finding the perfect solution, it's about finding the best solution for our specific use case, and that means making informed decisions about where we can afford to compromise.

## Availability, SLOs, and SLAs

One important measurement of a system is availability. This is the measure of a system's operational performance and reliability. When we talk about availability, we are essentially asking: is our system up and running when our users need it?

This is often measured in terms of percentage, aiming for that golden "five nines" availability. Let's say we are running a critical service with 99.9% availability: that allows for around 8.76 hours of downtime per year. But if we add two nines to it (99.999%), we are talking just about five minutes of downtime per year. That's a massive difference, especially for services where every second counts.

We often measure it in terms of uptime and downtime, and here is where service level objectives and service level agreements come into place.

**SLOs (Service Level Objectives)** are like setting goals for our system's performance and availability. For example, we might set an SLO stating that our web service should respond to requests within 300 milliseconds 99.9% of the time.

**SLAs (Service Level Agreements)** are like formal contracts with our users or customers. They define the minimum level of service we are committing to provide. So if our SLA guarantees 99.99% availability and we drop below that, we might have to provide refunds or other compensations to our customers.

**Building Resilience** into our system means expecting the unexpected. This could mean implementing redundant systems, ensuring there is always a backup ready to take over in case of failure. Or it could mean designing our system to degrade gracefully, so even if certain features are unavailable, the core functionality remains intact. To measure this aspect, we use:

- **Reliability**: Ensuring that our system works correctly and consistently
- **Fault Tolerance**: How does our system handle unexpected failures or attacks?
- **Redundancy**: Having backups, ensuring that if one part of our system fails, there is another ready to take its place

## Throughput and Latency

We also need to measure the speed of our system, and for that we have throughput and latency.

**Throughput** measures how much data our system can handle over a certain period of time.

- **Server throughput** is measured in requests per second (RPS). This metric provides an indication of how many client requests a server can handle in a given time frame. A higher RPS value typically indicates better performance and the ability to handle more concurrent users.
- **Database throughput** is measured in queries per second (QPS). This quantifies the number of queries a database can process in a second. Like server throughput, a higher QPS value usually signifies better performance.
- **Data throughput** is measured in bytes per second. This reflects the amount of data transferred over a network or processed by a system in a given period of time.

**Latency** measures how long it takes to handle a single request. It's the time it takes for a request to get a response.

Optimizing for one can often lead to sacrifices in the other. For example, batching operations can increase throughput but might also increase latency.

Designing a system poorly can lead to a lot of issues down the line, from performance bottlenecks to security vulnerabilities. Unlike code, which can be refactored easily, redesigning a system can be a monumental task. That's why it's crucial to invest time and resources into getting the design right from the start, laying a solid foundation that can support the weight of future features and user growth.

## Networking Basics

Now let's talk about networking basics. When we talk about networking basics, we are essentially discussing how computers communicate with each other.

**IP Addresses**: At the heart of this communication is the IP address, a unique identifier for each device on a network. IPv4 addresses are 32-bit, which allows for approximately 4 billion unique addresses. However, with the increasing number of devices, we are moving to IPv6 which uses 128-bit addresses, significantly increasing the number of available unique addresses.

**Data Packets**: When two computers communicate over a network, they send and receive packets of data. Each packet contains an IP header which contains essential information like the sender's and receiver's IP addresses, ensuring that the data reaches the correct destination. This process is governed by the Internet Protocol, which is a set of rules that defines how data is sent and received. Besides the IP layer, we also have the application layer where data specific to the application protocol is stored. The data in these packets is formatted according to specific application protocol data, like HTTP for web browsing, so that the data is interpreted correctly by the receiving device.

**TCP**: Once we understand the basics of IP addressing and data packets, we can dive into the transport layer, where TCP and UDP come into play. TCP operates at the transport layer and ensures reliable communication. It's like a delivery guy who makes sure that your package not only arrives but also checks that nothing is missing. Each data packet also includes a TCP header which is carrying essential information like port numbers and control flags necessary for managing the connection and data flow. TCP is known for its reliability. It ensures the complete and correct delivery of data packets. It accomplishes this through features like sequence numbers, which keep track of the order of packets, and the process known as the three-way handshake, which establishes a stable connection between two devices.

**UDP**: In contrast, UDP is faster but less reliable than TCP. It doesn't establish a connection before sending data and doesn't guarantee the delivery or order of the packets. But this makes UDP preferable for time-sensitive communications like video calls or live streaming, where speed is crucial and some data loss is acceptable.

**DNS (Domain Name System)**: To tie all these concepts together, let's talk about DNS. DNS acts like the internet's phone book, translating human-friendly domain names into IP addresses. When you enter a URL in your browser, the browser sends a DNS query to find the corresponding IP address, allowing it to establish a connection to the server and retrieve the web page. The functioning of DNS is overseen by ICANN, which coordinates the global IP address space and domain name system. Domain name registrars like Namecheap or GoDaddy are accredited by ICANN to sell domain names to the public. DNS uses different types of records like A records, which map the domain to its corresponding IPv4 address ensuring that your request reaches the correct server, or AAAA records, which map a domain name to an IPv6 address.

**Network Infrastructure**: Finally, let's talk about the networking infrastructure which supports all this communication. Devices on a network have either public or private IP addresses. Public IP addresses are unique across the internet, while private IP addresses are unique within a local network. An IP address can be static (permanently assigned to a device) or dynamic (changing over time). Dynamic IP addresses are commonly used for residential internet connections. Devices connected in a local area network can communicate with each other directly.

To protect these networks we use **firewalls**, which monitor and control incoming and outgoing network traffic. Within a device, specific processes or services are identified by **ports**, which when combined with an IP address create a unique identifier for a network service. Some ports are reserved for specific protocols, like 80 for HTTP or 22 for SSH.

## Application Layer Protocols

Now let's cover all the essential application layer protocols.

**HTTP (Hypertext Transfer Protocol)**: The most common protocol, built on TCP/IP. It's a request-response protocol. Imagine it as a conversation with no memory: each interaction is separate with no recollection of the past. This means that the server doesn't have to store any context between requests. Instead, each request contains all the necessary information. Notice how the headers include details like URL and method while the body carries the substance of the request or response.

Each response also includes the status code, which provides feedback about the result of a client's request on a server:

- **200 series**: Success codes, indicating the request was successfully received and processed
- **300 series**: Redirection codes, signifying further action needs to be taken by the user agent to fulfill the request
- **400 series**: Client error codes, used when the request contains bad syntax or cannot be fulfilled
- **500 series**: Server error codes, indicating something went wrong on the server

We also have a method on each request. The most common methods are GET, POST, PUT, PATCH, and DELETE. GET is used for fetching data. POST is usually for creating data on the server. PUT and PATCH are for updating a record. DELETE is for removing a record from the database.

**WebSockets**: HTTP is a one-way connection, but for real-time updates we use WebSockets that provide a two-way communication channel over a single long-lived connection, allowing servers to push real-time updates to clients. This is very important for applications requiring constant data updates without the overhead of repeated HTTP request-response cycles. It is commonly used for chat applications, live sport updates, or stock market feeds, where the action never stops and neither does the conversation.

**Email Protocols**:

- **SMTP**: The standard for email transmission over the internet. It is the protocol for sending email messages between servers. Most email clients use SMTP for sending emails and either IMAP or POP3 for retrieving them.
- **IMAP**: Used to retrieve emails from a server, allowing a client to access and manipulate messages. This is ideal for users who need to access their emails from multiple devices.
- **POP3**: Used for downloading emails from a server to a local client. Typically used when emails are managed from a single device.

**File Transfer and Management Protocols**:

- **FTP**: The traditional protocol for transferring files over the internet, often used in website maintenance and large data transfers. It is used for the transfer of files between a client and server, useful for uploading files to a server or backing up files.
- **SSH (Secure Shell)**: For operating network services securely on an unsecured network. It's commonly used for logging into a remote machine and executing commands or transferring files.

**Real-Time Communication Protocols**:

- **WebRTC**: Enables browser-to-browser applications for voice calling, video chat, and file sharing without internal or external plugins. This is essential for applications like video conferencing and live streaming.
- **MQTT**: A lightweight messaging protocol ideal for devices with limited processing power and in scenarios requiring low bandwidth, such as IoT devices.
- **AMQP**: A protocol for message-oriented middleware providing robustness and security for enterprise-level message communication. For example, it is used in tools like RabbitMQ.

**RPC (Remote Procedure Call)**: A protocol that allows a program on one computer to execute code on a server or another computer. It's a method used to invoke a function as if it were a local call, when in reality the function is executed on a remote machine. So it abstracts the details of the network communication, allowing the developer to interact with remote functions seamlessly as if they were local to the application.

Many application layer protocols use RPC mechanisms to perform their operations. For example, in web services, HTTP requests can result in RPC calls being made on the backend to process data or perform actions on behalf of the client. Or SMTP servers might use RPC calls internally to process email messages or interact with databases.

Of course there are numerous other application layer protocols, but the ones covered here are among the most commonly used and essential for web development.

## API Design

In this section let's go through the API design, starting from the basics and advancing towards the best practices that define exceptional APIs.

Let's consider an API for an e-commerce platform like Shopify, which if you're not familiar with, is a well-known e-commerce platform that allows businesses to set up online stores.

In API design we are concerned with defining the inputs (like product details for a new product, which is provided by a seller) and the outputs (like the information returned when someone queries a product) of an API. So the focus is mainly on defining how the CRUD operations are exposed to the user interface.

**CRUD** stands for Create, Read, Update, and Delete, which are the basic operations of any data-driven application. For example:

- To **add a new product**, we send a POST request to `/api/products` where the product details are sent in the request body
- To **retrieve products**, we send a GET request to `/api/products`
- For **updating**, we use PUT or PATCH requests to `/products/:id`
- For **removing**, it's DELETE to `/products/:id`
- We might also have another GET request to `/products/:id` which fetches a single product

Another part is to decide on the **communication protocol** that will be used (like HTTP, WebSockets, or other protocols) and the **data transport mechanism** (which can be JSON, XML, or Protocol Buffers).

### API Paradigms

This is usually the case for RESTful APIs, but we also have GraphQL and gRPC paradigms. APIs come in different paradigms, each with its own set of protocols and standards.

**REST (Representational State Transfer)**:
- Stateless, meaning each request from a client to a server must contain all the information needed to understand and complete the request
- Uses standard HTTP methods: GET, POST, PUT, and DELETE
- Easily consumable by different clients, browsers, or mobile apps
- Downside: can lead to overfetching or underfetching of data, because more endpoints may be required to access specific data
- Usually uses JSON for data exchange

**GraphQL**:
- Allows clients to request exactly what they need, avoiding overfetching and underfetching data
- Strongly typed queries
- Complex queries can impact server performance
- All requests are sent as POST requests
- GraphQL API typically responds with HTTP 200 status code even in case of errors, with error details in the response body

**gRPC (Google Remote Procedure Call)**:
- Built on HTTP/2, which provides advanced features like multiplexing and server push
- Uses Protocol Buffers, a way of serializing structured data
- Efficient in terms of bandwidth and resources, especially suitable for microservices
- Downside: less human-readable compared to JSON, and requires HTTP/2 support to operate

### API Best Practices

In an e-commerce setting, you might have relationships like user to orders or orders to products, and you need to design **endpoints to reflect these relationships**. For example, to fetch the orders for a specific user, you need to query GET `/users/:userId/orders`.

Common queries also include **limit and offset for pagination**, or start and end date for filtering products within a certain date range. This allows users or the client to retrieve specific sets of data without overwhelming the system.

A well-designed **GET request should be idempotent**, meaning calling it multiple times doesn't change the result and it should always return the same result. GET requests should never mutate data, they are meant only for retrieval. If you need to update or create data, you need to do a PUT or POST request.

When modifying endpoints, it's important to maintain **backward compatibility**. This means ensuring that changes don't break existing clients. A common practice is to introduce new versions, like `/v2/products`, so that the v1 API can still serve the old clients and v2 API should serve the current clients. This is in the case of RESTful APIs. In the case of GraphQL APIs, adding new fields (like v2 fields) without removing old ones helps in evolving the API without breaking existing clients.

Another best practice is to set **rate limitations**. This can prevent the API from DDoS attacks. It is used to control the number of requests a user can make in a certain time frame and prevents a single user from sending too many requests to your single API.

A common practice is to also set **CORS (Cross-Origin Resource Sharing)** settings. With CORS settings you can control which domains can access your API, preventing unwanted cross-site interactions.

## Caching and CDNs

Now imagine a company is hosting a website on a server in Google Cloud data centers in Finland. It may take around 100 milliseconds to load for users in Europe, but it takes 3 to 5 seconds to load for users in Mexico. Fortunately there are strategies to minimize this request latency for users who are far away. These strategies are called caching and content delivery networks, which are two important concepts in modern web development and system design.

**Caching** is a technique used to improve the performance and efficiency of a system. It involves storing a copy of certain data in a temporary storage so that future requests for that data can be served faster.

There are four common places where cache can be stored:

### Browser Caching

We store website resources on a user's local computer so when a user revisits a site, the browser can load the site from the local cache rather than fetching everything from the server again. Users can disable caching by adjusting the browser settings in most browsers. Developers can disable cache from the developer tools. For instance in Chrome, we have the "disable cache" option in the developer tools Network tab.

The cache is stored in a directory on the client's hard drive managed by the browser. Browser caches store HTML, CSS, and JS bundle files on the user's local machine, typically in a dedicated cache directory managed by the browser.

We use the **Cache-Control header** to tell the browser how long this content should be cached. For example, the cache control can be set to 7200 seconds, which is equivalent to 2 hours.

- **Cache hit**: When the requested data is found in the cache
- **Cache miss**: When the requested data is not in the cache, necessitating a fetch from the original source
- **Cache ratio**: The percentage of requests that are served from the cache compared to all requests. A higher ratio indicates a more effective cache.

You can check if the cache was hit or missed from the X-Cache header. For example, if it says "miss" the cache was missed, and in case the cache is found we will have "hit."

### Server Caching

Server caching involves storing frequently accessed data on the server side, reducing the need to perform expensive operations like database queries. Server-side caches are stored on a server or on a separate cache server, either in memory like Redis or on disk.

Typically the server checks the cache for the data before querying the database. If the data is in the cache, it is returned directly. Otherwise the server queries the database. If the data is not in the cache, the server retrieves it from the database, returns it to the user, and then stores it in the cache for future requests.

**Write strategies**:

- **Write-around cache**: Data is written directly to permanent storage, bypassing the cache. Used when write performance is less critical.
- **Write-through cache**: Data is simultaneously written to cache and the permanent storage. It ensures data consistency but can be slower than write-around cache.
- **Write-back cache**: Data is first written to the cache and then to permanent storage at a later time. This improves write performance, but you have a risk of losing that data in case of a crash of the server.

But what happens if the cache is full and we need to free up some space to use our cache again? For that we have **eviction policies**, which are rules that determine which items to remove from the cache when it's full. Common policies:

- **Least Recently Used (LRU)**: Remove the least recently used ones
- **First In First Out (FIFO)**: Remove the ones that were added first
- **Least Frequently Used (LFU)**: Remove the least frequently used ones

### Database Caching

Database caching is another crucial aspect and it refers to the practice of caching database query results to improve the performance of database-driven applications. It is often done either within the database system itself or via an external caching layer like Redis or Memcache.

When a query is made, we first check the cache to see if the result of that query has been stored. If it is, we return the cached data, avoiding the need to execute the query against the database. But if the data is not found in the cache, the query is executed against the database and the result is stored in the cache for future requests.

This is beneficial for read-heavy applications where some queries are executed frequently. We use the same eviction policies as we have for server-side caching.

### CDN (Content Delivery Network)

Another type of caching is CDNs, which are a network of servers distributed geographically. They are generally used to serve static content such as JavaScript, HTML, CSS, or image and video files. They cache the content from the original server and deliver it to users from the nearest CDN server.

When a user requests a file like an image or a website, the request is redirected to the nearest CDN server. If the CDN server has the cached content, it delivers it to the user. If not, it fetches the content from the origin server, caches it, and then forwards it to the user.

**Pull-based CDN**: The CDN automatically pulls the content from the origin server when it's first requested by a user. It's ideal for websites with a lot of static content that is updated regularly. It requires less active management because the CDN automatically keeps the content up to date.

**Push-based CDN**: You upload the content to the origin server and then it distributes these files to the CDNs. This is useful when you have large files that are infrequently updated but need to be quickly distributed when updated. It requires more active management of what content is stored on the CDNs.

We again use the **Cache-Control header** to tell the browser for how long it should cache the content from CDN.

CDNs are usually used for delivering static assets like images, CSS files, JavaScript bundles, or video content. It can be useful if you need to ensure high availability and performance for users. It can also reduce the load on the origin server.

But there are some instances where we still need to hit our origin server: for example when serving dynamic content that changes frequently, or handling tasks that require real-time processing, and in cases where the application requires complex server-side logic that cannot be done in the CDNs.

**Benefits of CDNs**:
- **Reduced latency**: By serving content from locations closer to the user, CDNs significantly reduce latency
- **High availability and scalability**: CDNs can handle high traffic loads and are resilient against hardware failures
- **Improved security**: Many CDNs offer security features like DDoS protection and traffic encryption

**Benefits of caching in general**:
- **Reduced latency**: Fast data retrieval since the data is fetched from the nearby cache rather than a remote server
- **Lower server load**: Reducing the number of requests to the primary data source, decreasing server load
- **Better user experience**: Overall faster load times

## Proxy Servers

Now let's talk about proxy servers, which act as an intermediary between the client requesting a resource and the server providing that resource. It can serve various purposes like caching resources for faster access, anonymizing requests, and load balancing among multiple servers. Essentially it receives requests from clients, forwards them to the relevant servers, and then returns the server's response back to the client.

### Types of Proxy Servers

There are several types of proxy servers, each serving different purposes:

- **Forward Proxy**: Sits in front of clients and is used to send requests to other servers on the internet. It's often used within internal networks to control internet access.
- **Reverse Proxy**: Sits in front of one or more web servers, intercepting requests from the internet. It is used for load balancing, web acceleration, and as a security layer.
- **Open Proxy**: Allows any user to connect and utilize the proxy server. Often used to anonymize web browsing and bypass content restrictions.
- **Transparent Proxy**: Passes along requests and resources without modifying them, but it's visible to the client. Often used for caching and content filtering.
- **Anonymous Proxy**: Identifiable as a proxy server but does not make the original IP address available. Used for anonymous browsing.
- **Distorting Proxy**: Provides an incorrect original IP to the destination server. Similar to an anonymous proxy but with purposeful IP misinformation.
- **High Anonymity (Elite) Proxy**: Makes detecting the proxy use very difficult. These proxies do not send X-Forwarded-For or other identifying headers and they ensure maximum anonymity.

### Forward Proxy

The most commonly used proxy servers are forward and reverse proxies. A forward proxy acts as a middle layer between the client and the server. It sits between the client (which can be a computer on an internal network) and the external servers (which can be websites on the internet).

When the client makes a request, it is first sent to the forward proxy. The proxy then evaluates the request and decides, based on its configuration and rules, whether to allow the request, modify it, or block it. One of the primary functions of a forward proxy is to hide the client's IP address. When it forwards the request to the target server, it appears as if the request is coming from the proxy server itself.

**Forward proxy use cases**:

- **Instagram proxies**: A specific type of forward proxy used to manage multiple Instagram accounts without triggering bans or restrictions. Marketers and social media managers use Instagram proxies to appear as if they are located in different areas or as different users, which allows them to manage multiple accounts, automate tasks, or gather data without being flagged for suspicious activity.
- **Internet use control and monitoring**: Some organizations use forward proxies to monitor and control employee internet usage. They can block access to non-related sites and protect against web-based threats. They can also scan for viruses and malware in incoming content.
- **Caching frequently accessed content**: Forward proxies can also cache popular websites or content, reducing bandwidth usage and speeding up access for users within the network. This is especially beneficial in networks where bandwidth is costly or limited.
- **Anonymizing web access**: People who are concerned about privacy can use forward proxies to hide their IP address and other identifying information from websites they visit, making it difficult to track their web browsing activities.

### Reverse Proxy

A reverse proxy is a type of proxy server that sits in front of one or more web servers, intercepting requests from clients before they reach the servers. While a forward proxy hides the client's identity, a reverse proxy essentially hides the server's identity or the existence of multiple servers behind it. The client interacts only with the reverse proxy and may not know about the servers behind it.

It also distributes client requests across multiple servers, balancing load and ensuring no single server becomes overwhelmed. Reverse proxies can also compress inbound and outbound data, cache files, and manage SSL encryption, thereby speeding up load time and reducing server load.

**Reverse proxy use cases**:

- **Load balancers**: Distribute incoming network traffic across multiple servers, ensuring no single server gets too much load. By distributing traffic, we prevent any single server from becoming a bottleneck, maintaining optimal service speed and reliability.
- **CDNs**: They are a network of servers that deliver cached static content from websites to users based on the geographical location of the user. They act as reverse proxies by retrieving content from the origin server and caching it so that it's closer to the user for faster delivery.
- **Web Application Firewalls (WAF)**: Positioned in front of web applications, they inspect incoming traffic to block hacking attempts and filter out unwanted traffic. Firewalls also protect the application from common web exploits.
- **SSL Offloading/Acceleration**: Some reverse proxies handle the encryption and decryption of SSL/TLS traffic, offloading that task from web servers to optimize their performance.

## Load Balancers

Load balancers are perhaps the most popular use cases of proxy servers. They distribute incoming traffic across multiple servers to make sure that no server bears too much load. By spreading the requests effectively, they increase the capacity and reliability of applications.

### Load Balancing Algorithms

Here are some common strategies and algorithms used in load balancing:

- **Round Robin**: The simplest form of load balancing where each server in the pool gets a request in sequential rotating order. When the last server is reached, it loops back to the first one. This type works well for servers with similar specifications and when the load is uniformly distributable.
- **Least Connections**: Directs traffic to the server with the fewest active connections. It's ideal for longer tasks or when the server load is not evenly distributed.
- **Least Response Time**: Uses the server with the lowest response time and fewest active connections. This is effective when the goal is to provide the fastest response to requests.
- **IP Hashing**: Determines which server receives the request based on the hash of the client's IP address. This ensures a client consistently connects to the same server and it's useful for session persistence in applications where it's important that the client consistently connects to the same server.
- **Weighted Algorithms**: Variants of the above methods can be weighted. For example, in weighted round robin or weighted least connections, servers are assigned weights typically based on their capacity or performance metrics, and the servers which are more capable handle the most requests. This is effective when the servers in the pool have different capabilities, like different CPU or different RAM.
- **Geographical**: Directs requests to the server geographically closest to the user or based on specific regional requirements. Useful for global services where latency reduction is a priority.
- **Consistent Hashing**: Uses a hash function to distribute data across various nodes. Imagine a hash space that forms a circle where the end wraps around to the beginning, often referred to as a hash ring. Both the nodes and the data (like keys or stored values) are hashed onto this ring. This makes sure that the client consistently connects to the same server every time.

### Health Checking

An essential feature of load balancers is continuous health checking of servers to ensure traffic is only directed to servers that are online and responsive. If a server fails, the load balancer will stop sending traffic to it until it is back online.

### Types of Load Balancers

Load balancers can be in different forms including hardware applications, software solutions, and cloud-based services.

**Hardware load balancers**:
- **F5 BIG-IP**: A widely used hardware load balancer known for its high performance and extensive feature set. It offers local traffic management, global server load balancing, and application security.
- **Citrix (formerly NetScaler)**: Provides load balancing, content switching, and application acceleration.

**Software load balancers**:
- **HAProxy**: A popular open-source software load balancer and proxy server for TCP and HTTP-based applications.
- **Nginx**: Often used as a web server but it also functions as a load balancer and reverse proxy for HTTP and other network protocols.

**Cloud-based load balancers**:
- AWS Elastic Load Balancing
- Microsoft Azure Load Balancer
- Google Cloud Load Balancer

**Virtual load balancers**:
- VMware's Advanced Load Balancer, which offers a software-defined application delivery controller that can be deployed on-premises or in the cloud.

### Handling Load Balancer Failure

Now let's see what happens when a load balancer goes down. When the load balancer goes down, it can impact the whole availability and performance of the application or services it manages. It's basically a single point of failure. In case it goes down, all of the servers become unavailable for the clients.

To avoid or minimize the impact of a load balancer failure, we have several strategies:

- **Redundant load balancing**: Using more than one load balancer, often in pairs, is a common approach. If one of them fails, the other one takes over, which is a method known as a failover.
- **Continuous monitoring and health checks**: Monitoring the load balancer itself can ensure that any issues are detected early and can be addressed before causing significant disruption.
- **Autoscaling and self-healing systems**: Some modern infrastructures are designed to automatically detect the failure of a load balancer and replace it with a new instance without manual intervention.
- **DNS failover**: In some configurations, DNS failover can reroute traffic away from an IP address that is no longer accepting connections (like a failed load balancer) to a pre-configured standby IP, which is our new load balancer.

## Databases

System design interviews are incomplete without a deep dive into databases. In the next few minutes, we'll go through the database essentials you need to understand to ace that interview. We'll explore the role of databases in system design, sharding and replication techniques, and the key ACID properties. We'll also discuss different types of databases, vertical and horizontal scaling options, and database performance techniques.

### Relational (SQL) Databases

We have different types of databases, each designed for specific tasks and challenges. The first type is relational databases. Think of a relational database like a well-organized filing cabinet where all the files are neatly sorted into different drawers and folders.

Some popular examples of SQL databases are PostgreSQL, MySQL, and SQLite. All of the SQL databases use tables for data storage and they use SQL as a query language. They are great for transactions, complex queries, and integrity.

Relational databases are also **ACID compliant**, meaning they maintain the ACID properties:

- **Atomicity**: Transactions are all or nothing
- **Consistency**: After a transaction, your database should be in a consistent state
- **Isolation**: Transactions should be independent
- **Durability**: Once a transaction is committed, the data is there to stay

### NoSQL Databases

We also have NoSQL databases, which drop the consistency property from ACID. Imagine a NoSQL database as a brainstorming board with sticky notes: you can add or remove notes in any shape or form, it's flexible.

Some popular examples are MongoDB, Cassandra, and Redis. There are different types of NoSQL databases such as:

- **Key-value pairs** like Redis
- **Document-based databases** like MongoDB
- **Graph-based databases** like Neo4j

NoSQL databases are schemaless, meaning they don't have foreign keys between tables which link the data together. They are good for unstructured data, ideal for scalability, quick iteration, and simple queries.

### In-Memory Databases

There are also in-memory databases. This is like having a whiteboard for quick calculations and temporary sketches. It's fast because everything is in memory. Some examples are Redis and Memcache. They have lightning-fast data retrieval and are used primarily for caching and session storage.

## Database Scaling

Now let's see how we can scale databases.

### Vertical Scaling (Scale Up)

The first option is vertical scaling or "scale up." In vertical scaling, you improve the performance of your database by enhancing the capabilities of the individual server where the database is running. This could involve increasing CPU power, adding more RAM, adding faster or more disk storage, or upgrading the network. But there is a maximum limit to the resources you can add to a single machine, and because of that it's very limited.

### Horizontal Scaling (Scale Out)

The next option is horizontal scaling or "scale out," which involves adding more machines to the existing pool of resources rather than upgrading the single unit. Databases that support horizontal scaling distribute data across a cluster of machines. This could involve database sharding or data replication.

**Database Sharding**: Distributing different portions (shards) of the dataset across multiple servers. This means you split the data into smaller chunks and distribute it across multiple servers. Some of the sharding strategies include:

- **Range-based sharding**: Distribute data based on the range of a given key
- **Directory-based sharding**: Utilizing a lookup service to direct traffic to the correct database
- **Geographical sharding**: Splitting databases based on geographical locations

**Data Replication**: Keeping copies of data on multiple servers for high availability.

- **Master-slave replication**: Where you have one master database and several read-only slave databases
- **Master-master replication**: Multiple databases that can both read and write

## Database Performance Techniques

Scaling your database is one thing, but you also want to access it faster. So let's talk about different performance techniques that can help to access your data faster.

- **Caching**: Caching isn't just for web servers. Database caching can be done through in-memory databases like Redis. You can use it to cache frequent queries and boost your performance.
- **Indexing**: Indexes are another way to boost the performance of your database. Creating an index for frequently accessed columns will significantly speed up retrieval times.
- **Query Optimization**: You can also consider optimizing queries for fast data access. This includes minimizing joins and using tools like SQL Query Analyzer or EXPLAIN PLAN to understand your query's performance.

In all cases, you should remember the CAP theorem, which states that you can only have two of these three: consistency, availability, and partition tolerance. When designing a system, you should prioritize two of these based on the requirements that you have been given in the interview.

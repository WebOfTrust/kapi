# Keri API (KAPI)
## Overview

The various components in the KERI ecosystem such as Controllers, Agents, Witnesses, Watchers, Registrars etc need application programmer interfaces (APIs) by which they can share information. The unique properties of the KERI protocol require APIs that preserve those properties. We call the set of APIs the KERI API, or KAPI for short. This means that conventional approaches to API design must be adapted to take advantage of the unique features of the KERI stack. The main protocols in the KERI stack are CESR, KERI, and ACDC. These include sub-protocols such as SAID, OOBI, IPEX, and SAD Path Signatures.

One salient feature of the KERI stack is secure attributability to unbounded term cryptographic identifiers (AIDs). There are different levels of secure attribution, namely KEL sealed (anchored), BADA-RUN, and KRAM. Another salient feature is the transport-agnostic CESR streaming protocol. Another salient feature is self-addressing data using embedded cryptographic digests (SAIDs). The API design for the KERI stack should take advantage of the salient features and not get in their way. 

All that said, there is an advantage to leverage pre-existing design patterns for API design, if for no other reason than familiarity to developers. In many cases, those pre-existing design patterns reflect lessons well learned and are backed by tooling. A KAPI design aims to exploit those cases where pre-existing design patterns can be conveniently adapted to the salient KERI features.

The first API design pattern that was adapted are web APIs (ReST). There was some extensive discussion about how to make that adaptation (see [Query Mode](https://github.com/decentralized-identity/keri/issues/109)). This was adapted from useful guidelines for Web (ReST) API design (See [Web API Design](https://cloud.google.com/files/apigee/apigee-web-api-design-the-missing-link-ebook.pdf), and [API Design](https://pages.apigee.com/rs/apigee/images/api-design-ebook-2012-03.pdf)). 

The first problem in leveraging web API design is that web APIs are based on the HTTP protocol. This protocol is based on a client-server architecture that depends on the synchronous TCP/IP transport protocol. Meanwhile, CESR/KERI is an asynchronous peer-to-peer architecture that is transport agnostic. The CESR protocol is a streaming protocol that can sit atop either synchronous streaming transports or asynchronous datagram transports. In contrast, HTTP is a datagram protocol that sits on top of a reliable synchronous streaming transport (TCP/IP). This means HTTP's synchronous client-server request-response pattern must be adapted to an asynchronous peer-to-peer exchange. It would be advantageous if the native KAPI could be mapped to an HTTP web interface. Likewise, it would be advantageous if the native KAPI could be mapped to a command line interface (CLI).

## Location is Function

One of the abstract features of a Web API is that *location-is-function*. A URL maps a location to a resource, and an HTTP verb operates on that resource. The location is specified with a path and parameters. This parameterizes the function at that location. The path is hierarchical which supports hierarchical composition of functions. This "location is function" abstraction is very powerful; it fosters legible APIs that can be built and managed hierarchically and incrementally. Familiar best practices and lessons learned are well-baked into tooling. Hierachical location enables routing amongst compoents so that a "backend" can be distributed. Although there are other API abstractions besides "location is function", the familiarity and tooling associated with this web API abstraction make it the most attractive starting point.

### Routing in KERI

The native KERI approach to *location-is-function* that maps to the web request paradigm is a message that contains a route, `r` field at its top level. KERI message types with a route, `r` field are classified as "routable" messages. The value of the route field is a path that maps to or is analogous to the base path of a URL. This path is not a URL. HTTP depends on some unique features of the URL mini-language and also suffers from its limitations (like relatively short length). As a result the URL syntax is not supported but instead a syntax that can be mapped to a URL based HTTP request.

In KAPI, a route is a simple slash, `/` delimited path that is not parametrized.  This removes the need for special characters to support such inline parameters. Special CESR Text Domain versions of a route are now supportable.  All URL like parameters such as path parameters, query parameters, or form parameters become attributes of a routable message body. This better supports CESR streaming of either native CESR serialized message bodies or embedded JSON, CESR, or MGPK serialized message bodies.

The route path (location) is an abstraction that indicates a service location in detail. The actual "address" of the service includes the transport mechanism and may be relative to an IP service endpoint address provided by an OOBI. 

A route may be absolute or relative. An absolute route starts with a slash, `/` character. A relative route does not. For example, `/log/process` is absolute; `log/process` is relative. In many cases, the expression of the route as either absolute or relative will not matter. This is dependent on how the routing internals are handled. In those cases, relative routes are slightly more compact. When expressed as native CESR paths, however, absolute routes remove an encoding ambiguity. 

Unless otherwise specified, absolute and relative routes should resolve to the same route. This means a router may either strip the leading slash or add a leading slash when missing. 

A route that ends in a slash is a directory that returns other routes. For example, `/log/` (absolute), `log/` (relative) returns a directory of routes that start with itself, `/log/` or `log/`. This provides a normative mechanism for discovering routes. A query of a given route directory could return detailed documentation of using that route.

The root directory route, `/` (absolute), `` (relative) is special. It provides a directory of all the routes served by the given endpoint. This provides a global discovery mechanism of all the routes at an endpoint.


### Routed Services

Using hierarchical routes to manage services is a powerful paradigm for both externally and internally facing APIs. By abstracting the route concept so that it is not tied to the narrow confines of ReST URL based APIs, and also combining that abstraction with OOBIs that map transport schemes to AIDs, a KERI implementation can use routing across its distributed infrastructure as a unifying architectural property.  

For example, once a message has been received at a transport-specific port and the appropriate authentication (secure attribution) policy has been applied, it can be forwarded to a router that distributes the message to the process that handles it. One way to effect that distribution is to prefix the external route provided in the message with an internal route that redirects the message appropriately. Thus, routing can be used to organize the external-facing API and any internal-facing APIs. A return route enables the response to be returned despite asynchronous internal processing of the request. With this approach, no artificial synchronous state must be maintained to match outgoing and incoming messages. The internal routes can reflect different types of routing such as intra-process, inter-process, inter-host, inter-protocol, inter-database. 

A given implementation could have multiple types of routers each with different properties including security properties.

A more detailed exposition of a distributed routed services architecture may be found here, [Many Cubed](https://github.com/SmithSamuelM/Papers/blob/master/whitepapers/ManyCubed.md).

#### Router(s)

Some types of routers include: inter-host router, inter-protocol transport router,  inter-process router, and intra-process router.  These router types can be mixed and matched with an appropriate design of routing prefixes. This internal routing could be completely transparent to any external interface because the routing prefixes would be attached and then stripped as appropriate—only the external portion of a route needs to be exposed as part of the external API.

Web APIs use something called middleware to achieve similar results. A middleware stack allows a router to manage how messages are processed differentially by redirecting the message through middleware. Here instead of a middleware stack a routing prefix is used. The route can then index the flow through a middleware stack. The route prefix is determinative.

For example, suppose that an internal query/reply/exchange router manages some routes. This router may be configured to distribute the various routes across multiple asynchronous coroutines, all running on the same process. This is how the current keripy implementation leverages the Hio asynchronous IO framework. 

This could be extended to support multiple processes on multiple cores with an inter-process router. Each process would have its own route prefix that would allow a given message to be routed internally between processes thus increasing the throughput of the host. 

This could be further extended to support multiple host machines in a data center with an inter-host router. Each host would have a route prefix added to the inter-process prefix, thereby allowing a given message to be routed to a different process on different hosts. 

The type of transport is abstracted via the route prefix.  This essentially defines a convenient economical software defined processing architecture. This maps to many architecture types: event sourcing, pub-sub, micro-services, and function-as-a-service.

#### Routing Security

Suppose further that some information needs to be protected as sealed confidential. A KEL conveys two types of information:

- information that is public to the KEL, namely key state. In general, key state includes not just the current signing keys but all the associated information including thresholds for both signing keys, next pre-rotated key digests, witness pool identifiers and threshold and configuration data. Any viewer of a KEL can view this key state. Thus, the publicity of the KEL itself determines the publicity of its key state data. Other public information may be sealed to a KEL. The seal itself is a cryptographic digest that does not disclose the data. Still, if the associated data is provided elsewhere in a public manner, then the seal provides no confidentiality protection but merely a verifiable binding. An example of this type of data is a transaction event log used for a revocation registry for an ACDC.

- information that is hidden but sealed to the key state in the KEL. A seal includes a cryptographic digest of information. The presence of the seal in an event in the KEL binds that data to the key state at that event but without disclosing the information. Thus the binding is public but the information is not. When the information includes sufficient cryptographic entropy, such as through the inclusion of a salty-nonce (UUID) then an attacker can not discover that data even with a rainbow table attack. The digest effectively hides or blinds the data. This enables the data to be protected or treated as sensitive or confidential. Access to the KEL does not disclose the data. Some other exchange process is required to disclose or un-blind the data. This type is appropriate for sealed confidential information.

One security vulnerability of routed architectures is attacks on the routers themselves (especially router configuration, both static and dynamic). This vulnerability is most acute when a single router must handle information with different security properties. The two most common infrastructure vulnerabilities are BOLA (Broken Object Level Authorization) and BUA (Broken User Authentication) attacks. These often exhibit as exploits on the routing process itself. Indeed, one of the weaknesses of virtual private network protocols is the difficulty to correctly securely configure routing on the private side of the VPN access router.

One solution to this problem is to use a pre-router that can redirect messages to different post-routers with differnt security properites.  For example, a pre-router would route sensitive data to a sensitive data post-router and non-sensitive data to a non-sensitive data post-router. This ensures that sensitive and non-sensitive data are never mixed. This enables tighter, more secure configuration control over data flows within an infrastructure. The best pre-routers act early in the routing process.

In KERI, the earliest possible place for a pre-router is at the stream parser. The stream parser does not look at routes but does look at message types, therefore a stream parser as pre-router needs the sensitive data to be segregated by message type. As a result, the KERI protocol supports two classes of routed messages distinguished by message types. The first class is denoted by
query-reply-exchange messages, and the second by prod-bare messages. The first class, query-reply-exchange may used for the first type of information above, namely information public to a KEL. The second class, prod-bare may be used for the second type of information, namely hidden but sealed to a KEL (sealed confidential). When a given implementation chooses to use one router for both classes of information, it must take appropriate measures to protect the router.  

Notable is that the exchange message types are only associated with the first class of data. This is because exchange messages are signed by the participating peers but not sealed. Once an exchange transaction is completed successfully, the set of messages in that transaction may be aggregated and then sealed to the participating peer's KELs. The transaction set may then be treated as sealed confidential infomation and its subsequent disclosure managed with prod-bare messages. An exchange message may reference a data item that is sealed but the disclosure of that seal may happen with a bare, `bar` message. Often, the point of an exchange is to negotiate a chain-link confidential disclosure of information. The detailed disclosure may happen out-of-band to the exchange that negotiates the contractual commitments to that data. Those commitments use cryptographic digests that maintain confidentiality. Later disclosure of the information may be facilitated with a prod-bare pair.


### Routable Message Types
The routable message types are as follows:

|Type|Title|Description|
|---|---|---|
|     |  **Routed Messages** | |
|`qry`| Query | request for data, a solicitation. |
|`rpy`| Reply | data either unsolicited or in response to a query solicitation. |
|`xip`| Exchange Inception| peer-to-peer exchange initiation. Incepts multi-exchange message transaction. The first exchange message in a transaction set. |
|`exn`| Exchange | peer-to-peer exchange. Generic exchange. may be a member of a multi-message transaction set. |
|`pro`| Prod | request for sealed confidential data, a solicitation.|
|`bar`| Bare | sealed confidential data, either unsolicited or in response to a prod solicitation. |


These message types are described below.

### Top-level Reserved Fields

Routable messages may include a subset of the following top-levels fields. 

|Label|Title|Description|
|---|---|---|
|`v`| Version String | enables regex parsing of field map in CESR stream |
|`t`| Message Type | three character string|
|`d`| Digest SAID | fully qualified digest of block in which it appears|
|`i`| Identifier Prefix (AID) | fully qualified primitive, Controller AID or sender |
|`x`| Exchange Identifier (SAID) | fully qualified unique identifier for an exchange transaction |
|`p`| Prior SAID | fully qualified digest, prior message SAID in an exchange transaction |
|`dt`| ISO date/time string |
|`r`| Route | delimited path string for routing message|
|`rr`| Return Route | delimited path string for routing a response to a solicitation message |
|`q`| Query Map | field map of query like parameters |
|`a`| Attribute Map  | field map of message attributes | 


####  Version String

All KERI routable messages that are serialized in JSON, CESR, or MGPK  include a version string, `v` field. This is defined in detail in the CESR protocol specification. KERI messages that are serialized in native CESR include a protocol version field instead of a version string field.

####  Message Type

All KERI routable messages include a message type, `t` field. This is defined in detail in the KERI protocol specification.

####  SAID

All KERI routable messages include a SAID (digest), `d` field. This is defined in detail in the KERI protocol specification. Its value is the SAID of the message.

#### AID

All KERI routable messages include a sender controller AID, `i` field at the top-level.  When the Controller Identifier AID, `i` field appears at the top-level of a Routed Message, it refers to the Controller AID of the sender of that message. A Controller AID, `i` field may appear in other places in messages. In those cases, its meaning is determined by the context of its appearance.

#### Prior event SAID field

The prior, `p` field is the SAID of the prior exchange message in a transaction. When the prior `p` field appears in an exchange message, its value shall be the SAID of the immediately preceding exchange message in that transaction. When an exchange message is not part of a transaction, then the prior `p` field value shall be the empty string. 

#### Exchange identifier field

The Exchange Identifier SAID, `x` field value shall be the SAID, `d` field value of the first message in the set of exchange messages that constitute a transaction. The first message shall be an Exchange Inception message with type `xip`.  The SAID, `d` field value of the Exchange Inception message is strongly bound to the details of that message. As a cryptographic strength digest, it is a universally unique identifier. Therefore, the appearance of that value as the Exchange identifier, the `x` field in each subsequent exchange message in a transaction set, universally uniquely associates them with that set. Furthermore, the prior `p` field value in each subsequent exchange message verifiably orders the transaction set in a duplicity-evident way. When an exchange message is not part of a transaction, the Exchange Identifier, `x` field value, shall be the empty string. 


#### Datetime, `dt` field
The datetime, `dt` field value, if any, shall be the ISO-8601 datetime string with microseconds and UTC offset as per IETF RFC-3339.  In a given field map (block) the primary datetime will use the label, `dt`. The usage context of the message and the block where a given DateTime, `dt` field appears determines which clock (sender or receiver) the datetime is relative to.

 An example datetime string in this format is as follows:

`2020-08-22T17:50:09.988921+00:00`


#### Route field

The Route, `r` field value is a '/' delimited string that forms a path. This indicates the target of a given message that includes this field. This enables the message to replicate the function of the path in a ReST resource. When used in an Exchange Transaction Inception, `xip` or Exchange, `exn` message, the Route, `r` field value defines both the type of transaction and a step within that transaction. For example, suppose that the route path head value, `/ipex/` means that the transaction type is an issuance and presentation exchange transaction and the full route path value, `/ipex/offer` means that the message is the `offer` step in such a transaction.

#### Return Route field

The Return Route, `rr` field value is a '/' delimited string that forms a path. This allows a message to indicate how to target the associated response to the message. This enables messages on asynchronous transports to associate a given response with the message that triggered the response.

#### Query field

The Query, `q` field value is a field map (block). Its fields provide the equivalent of query parameters in a ReST resource.

#### Attribute field

The Attribute, `a` field value is a field map (block). Its fields provide the attributes conveyed by the message.


## Routed Message Usage

### Query and Reply

In addition to its route, `r` field a query, `qry` message also has a return route, `rr` field. The return route, `rr`, field value is also a slash, `/` delimited path. The return route field value a query, `qry` becomes the route field value in the associated reply, `rpy` message. This enables a query-reply pair to be matched over asynchronous peer-to-peer channels. A KERI query-reply pair is analogous to an HTTP request-response pair.

When a reply message is sent in response to a query it is considered a *solicited* reply, this supports *pull* architectures. 

When a reply is sent without being triggered directly by a query it is considered an *unsolicited* reply, this supports *push* architectures.

#### Example
The following is an example of a query-replay pairing:

The query, `q`, field block in the query, `qry` message below contains the parameters for the data solicitation at route `/log`. Notice that the return route, `rr` field value, is also provided.

```json
{
  "v": "KERICAAJSONAACd.",
  "t": "qry",
  "d" : "EH3ULaU6JR2nmwyvYAfSVPzhzS6b5CMZ-i0d8JZAoTNZ",
  "i" : "EAfSVPzhzS6b5CMZ-i0d8JZAoTNZH3ULaU6JR2nmwyvY",
  "dt": "2020-08-22T17:50:12.988921+00:00",
  "r": "/log",
  "rr": "/log/process",
  "q":
  {
    "d": "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
    "i" : "EAoTNZH3ULvYAfSVPzhzS6baU6JR2nmwyZ-i0d8JZ5CM",
    "s": "5",
    "dt": "2020-08-01T12:20:05.123456+00:00",
  }
}
```

When using non-interactive KRAM authentication for the query above, the `i` field is the AID of the sender of the query, which may be used to look up its associated key state to verify an attached signature. The DateTime, `dt` field is relative to the receiver's clock, which uses it to determine if the query is a replay.

Notice that the route field, `r` value in the reply is set to the return route field value in the associated query. The attribute, `a`, field block in the reply, `rpy` message below contains data to be processed. 


```json
{
  "v": "KERI10JSON00011c_",
  "t": "rpy",
  "d": "EH3ULaU6JR2nmwyvYAfSVPzhzS6b5CMZ-i0d8JZAoTNZ",
  "i" : "EAfSVPzhzS6b5CMZ-i0d8JZAoTNZH3ULaU6JR2nmwyvY",
  "dt": "2020-08-22T17:50:12.988921+00:00",
  "r":  "/log/process",
  "a" :
  {
    "d":  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
    "i": "EAoTNZH3ULvYAfSVPzhzS6baU6JR2nmwyZ-i0d8JZ5CM",
    "name": "John Jones",
    "role": "Founder",
  }
}
```

When using BADA-RUN on the reply above, the `i` field is the AID of the sender of the reply, which may be used to look up its associated key state to verify an attached signature. The DateTime, `dt` field is relative to the reply sender's clock. The recipient of the reply uses it to determine the monotonicity of the update contained in the reply data.

### Exchange

Peer-to-peer message exchange or peer-to-peer transactioned message exchange.

When used in an exchange message, the Route, `r` field value defines both the type of transaction and a step within that transaction. For example, a route path of `/ipex/` is a directory of routes (steps) in the ipex (issuance and presentation exchange) transaction type. A full route path value, `/ipex/offer` indicates the actual step. In this case itmeans that the message is the `offer` step in such a transaction. Because each transaction type corresponds to a pre-defined state machine with known next steps for each step (route), there is no need for a return route field. 

A non-transactioned exchange message has only one effective step, so its route is just the type of exchange. A non-transactioned message may use the exchange, `exn` message type.

When the prior `p` field appears in an exchange message, its value shall be the SAID of the immediately preceding exchange message in that transaction. When an exchange message is not part of a transaction, then the prior `p` field value shall be the empty string. 

The Exchange Identifier SAID, `x` field value shall be the SAID, `d` field value of the first message in the set of exchange messages that constitute a transaction.  When an exchange message is not part of a transaction, the Exchange Identifier, `x` field value, shall be the empty string. The first message in an exchange transaction set shall be an Exchange Inception message with type `xip`.  The SAID, `d` field value of the Exchange Inception message is strongly bound to the details of that message. As a cryptographic strength digest, it is a universally unique identifier. Therefore, the appearance of that value as the Exchange identifier, the `x` field in each subsequent exchange message in a transaction set, universally uniquely associates them with that set. Furthermore, the prior `p` field value in each subsequent exchange message verifiably orders the transaction set in a duplicity-evident way.

#### Example

```json
{
  "v": "KERICAAJSONAACd.",
  "t": "xip",
  "d": "EF3Dd96ATbbMIZgUBBwuFAWx3_8s5XSt_0jeyCRXq_bM",
  "i": "EBBwuFAWx3_8s5XSt_0jeyCRXq_bMF3Dd96ATbbMIZgU",
  "dt": "2021-11-12T19:11:19.342132+00:00",
  "r": "/ipex/offer",
  "q": {},
  "a": 
  {
    "msg": "test ipex"
  }
}
```
```json
{
  "v": "KERICAAJSONAACd.",
  "t": "exn",
  "d": "EF3Dd96ATbbMIZgUBBwuFAWx3_8s5XSt_0jeyCRXq_bM",
  "i": "EMF3Dd96ATbbMIZgUBBwuFAWx3_8s5XSt_0jeyCRXq_b",
  "x": "EF3Dd96ATbbMIZgUBBwuFAWx3_8s5XSt_0jeyCRXq_bM",
  "p": "EDd96ATbbMIZgUBBwuFAWx3_8s5XSt_0jeyCRXq_bMF3",
  "dt": "2021-11-12T19:11:19.342132+00:00",
  "r": "/ipex/agree",
  "q": {},
  "a": 
  {
    "msg": "test ipex"
  }
}
```

### Query-Reply-Exchange Security Properties

The security properties of query-reply-exchange messages reflect the type of data involved. The messages are assumed to be no more secure than KRAM for query and BADA-RUN for reply and exchange.  Suppose a reply or exchange message includes or references data that is sealed (anchored) on a KEL. In that case, the recipient of the replay may verify that seal and therefore elevate the security properties of that data. Importantly, the router of query-reply-exchange messages cannot be assumed to be any more secure than KRAM/BADA-RUN. More secure data handling and routing can be handled with prod-bare messages, which can utilize a more secure router triggered by such messages. 

#### Query-Reply-Exchange Interoperability

In general, solicited query-reply message pairs and unsolicited reply messages with routes and return routes can map all the services a given KERI component needs to provide for accessing KEL-related data. Moreover, exchange messages either transactioned or not can map all the services for peer-to-peer exchange of data. A given provider can decide on their routes and document them for others to use. Better interoperability is realized when there is a standard set of route definitions, query parameter definitions, reply attribute definitions, and exchange attribute definitions that all providers share. The route directory section below is where standard routes, parameters, and attributes are defined.


### Prod and Bare
Sealed Confidential Data Handling.
Independent router from Query/Reply/Exn router

Generaly used to disclosed sealed confidential data. A special case is to capture, seal, and disclose completed exchange transaction sets.



```json
{
  "v": "KERICAAJSONAACd.",
  "t": "pro",
  "d": "EH3ULaU6JR2nmwyvYAfSVPzhzS6b5CMZ-i0d8JZAoTNZ",
  "i" : "EAfSVPzhzS6b5CMZ-i0d8JZAoTNZH3ULaU6JR2nmwyvY",
  "dt": "2020-08-22T17:50:12.988921+00:00",
  "r": "/sealed/data",
  "rr": "/sealed/data/process",
  "q":
  {
    "d": "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
    "i": "EAoTNZH3ULvYAfSVPzhzS6baU6JR2nmwyZ-i0d8JZ5CM",
    "s": "5",
    "ri": "EAoTNZH3ULvYAfSVPzhzS6baU6JR2nmwyZ-i0d8JZ5CM",
    "dd": "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM"
  }
}
```

```json
{
  "v": "KERICAAJSONAACd.",
  "t": "bre",
  "d": "EH3ULaU6JR2nmwyvYAfSVPzhzS6b5CMZ-i0d8JZAoTNZ",
  "i" : "EAfSVPzhzS6b5CMZ-i0d8JZAoTNZH3ULaU6JR2nmwyvY",
  "dt": "2020-08-22T17:50:12.988921+00:00",
  "r": "/sealed/data/process",
  "a":
  {
    "d": "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
    "i": "EAoTNZH3ULvYAfSVPzhzS6baU6JR2nmwyZ-i0d8JZ5CM",
    "dt": "2020-08-22T17:50:12.988921+00:00",
    "name": "John Jones",
    "role": "Founder",
  }
}
```
### Prod-Bare Security Properties

The security properties of prod-bare messages reflect the type of data involved. The messages are assumed to be securely bound to key states and undisclosable data without explicit disclosure; hence, they can be protected as confidential (sensitive) data. More secure data handling and routing can be handled with prod-bare messages, which can utilize a more secure router triggered by such messages. 

#### Prod-Bare Interoperability

In general, solicited prod-bare message pairs and unsolicited bare messages with routes and return routes can map all the services a given KERI component needs to provide for accessing sealed confidential data. A given provider can decide on their routes and document them for others to use. Better interoperability is realized when there is a standard set of route definitions, prod parameter definitions, and bare attribute definitions that all providers share. The route directory section below is where standard routes, parameters, and attributes are defined.


## Route Directory

### Roles

|Role|Description|
|---|---|
| `controller` | |
| `agent` | |
| `witness` | |
| `watcher` | |
| `juror` | |
| `judge` | |
| `registrar` | |

### Route Discovery

Directory routes ending in slash, `/` enable discovery of other routes.  

OOBI and well-known routes enable dicovery of other KERI components by role and service endpoint hosts.

#### Well-known Routes

|Route| Role(s) |Description|
|---|---|---|
|`/`| All | Route Directory provided by host, empty string "" for relative route |
|`/oobi/`| All | Directory of OOBIs provided by host |
|`/ipex/`| Controller, Agent | Directory of IPEX exchange routes|
|`/kel/`| All | Directory of KELs provided by host |

#### Well-known URLS

[IETF RFC-8615](https://www.rfc-editor.org/rfc/rfc8615.html)  `/.well-known/` URLs for KERI stack.


|URL| Role(s) |Description|
|---|---|---|
|`/`| All | Route Directory provided by host, empty string "" for relative route |
|`/oobi/`| All | Directory of OOBIs provided by host |
|`/kel/`| All | Directory of KELs provided by host |

### OOBIs

Directory of OOBIS that map host ip addresses and schemes to AIDs and roles.
An OOBI directory is analogous to a hostname table.
The OOBIs enable redirects to other hosts and roles.

#### OOBI Route Table
|Route| Description |
|---|---|
|`/oobi/{CID}/witness/{EID}`| Controller CID, witness EID|
|`/oobi/{AID}`|  AID  of some role|


#### OOBI URL Table

|URL| Description |
|---|---|
|`http://8.8.5.6:8080/oobi/{CID}/witness/{EID}`| Controller CID, witness EID| 
|`http://8.8.5.6:8080/oobi/{EID}?role=watcher&name=eve`|  Watcher EID named eve |


### Controller Routes

|Route| Role(s) |Description|
|---|---|---|
|`/`| All | Route Directory provided by host, empty string "" for relative route |
|`/oobi/`| All | Directory of OOBIs provided by host |
|`/ipex/`| Controller, Agent | Directory of IPEX exchange routes|
|`/ipex/apply`| Controller, Agent | ipex apply|
|`/ipex/offer`| Controller, Agent | ipex offer|
|`/ipex/agree`| Controller, Agent | ipex agree|
|`/ipex/grant`| Controller, Agent | ipex grant|
|`/ipex/admit`| Controller, Agent | ipex admit|
|`/ipex/spurn`| Controller, Agent | ipex spurn|
|`/kel/`| All | Directory of KELs provided by host |


### Witness Routes

|Route| Role(s) |Description|
|---|---|---|
|`/`| All | Route Directory provided by host, empty string "" for relative route |
|`/oobi/`| All | Directory of OOBIs provided by host |
|`/kel/`| All | Directory of KELs provided by host |
|`/tel/`| All | Directory of TELs provided by host |


### Watcher Routes

|Route| Role(s) |Description|
|---|---|---|
|`/`| All | Route Directory provided by host, empty string "" for relative route |
|`/oobi/`| All | Directory of OOBIs provided by host |
|`/kel/`| All | Directory of KELs provided by host |
|`/tel/`| All | Directory of TELs provided by host |


### Registrar Routes

|Route| Role(s) |Description|
|---|---|---|
|`/`| All | Route Directory provided by host, empty string "" for relative route |
|`/oobi/`| All | Directory of OOBIs provided by host |
|`/kel/`| All | Directory of KELs provided by host |
|`/tel/`| All | Directory of TELs provided by host |

### All Routes

| Route                 | Role(s)           | Description                                                          |
|-----------------------|-------------------|----------------------------------------------------------------------|
| `/`                   | All               | Route Directory provided by host, empty string "" for relative route |
| `/oobi/`              | All               | Directory of OOBIs provided by host                                  |
| `/ipex/`              | Controller, Agent | Directory of IPEX exchange routes                                    |
| `/ipex/admit`         | Controller, Agent | Ipex admit                                                           |
| `/ipex/agree`         | Controller, Agent | Ipex agree                                                           |
| `/ipex/apply`         | Controller, Agent | Ipex apply                                                           |
| `/ipex/grant`         | Controller, Agent | Ipex grant                                                           |
| `/ipex/offer`         | Controller, Agent | Ipex offer                                                           |
| `/ipex/spurn`         | Controller, Agent | Ipex spurn                                                           |
| `/kel/`               | All               | Directory of KELs provided by host                                   |
| `/tel/`               | All               | Directory of TELs provided by host                                   |
| `/mbx`                | All               | KERI mailbox                                                         |
| `/logs`               | All               | Key event log route                                                  |
| `/ksn/`               | All               | Directory of Key state notices                                       |
| `/tsn/`               | All               | Directory of Transaction State Notices                               |
| `/tsn/registry`       | All               | Transaction State Notices Registry                                   |
| `/tsn/credential`     | All               | Transaction State Notices Credential                                 |
| `/multisig/icp`       | All               | Incept group multisig                                                |
| `/multisig/exn`       | All               | Multisig group interaction                                           |
| `/multisig/iss`       | All               | Multisig cred issuance                                               |
| `/multisig/rev`       | All               | Multisig cred revocation                                             |
| `/multisig/rot`       | All               | Rotate group multisig                                                |
| `/multisig/rpy`       | All               | Handle multisig reply messages                                       |
| `/multisig/vcp`       | All               | Multisig registry inception event                                    |
| `/challenge/response` | All               | Peer to peer challenge response                                      |
| `/loc/scheme`         | All               | Location schemes route                                               |
| `/end/role/`          | All               | Directory of add/cut roles                                           |
| `/end/role/add`       | All               | Add roles                                                            |
| `/end/role/cut`       | All               | Cut roles                                                            |


## Web API Mapping

OpenAPI documentation for the ReST Web API equivalents of the routes above.

## CLI Mapping

Help documentation for the CLI equivalents of the routes above.




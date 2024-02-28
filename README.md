# About the Debug Tool

Debug Tool is a network analysis tool which analyzes the network call logs using a csv file which is of the format used by Charles Proxy. 
It is capable of generating graphs for network calls indicating their status code, request time, latency and response time. It currently has two filter features. One feature helps in 
featuring the network calls based on the Ad Network Calls & second filtering feature capable of adding custom domain names to filter network calls. 

# Setting up tool & environment

To use the tool, follow the instructions below to clone the project to your system - 

a. type the given command in your terminal                                  
```
git clone https://github.com/tanmaycrackle/DebugTool
```
b. navigate to the project directory
c. Install python in your system if it is not already installed
d. Install virtual environment                                              
```
pip install virtualenv
```
e. Create virtual environment                                               
```
virtualenv venv
```
f. Activate the virtual environment

For windows 
```
venv\Scripts\activate
```
For macOS/ linux 
```
source venv/bin/activate
```
g. Install the dependencies required                                        
```
pip install -r requirements.txt
```
h. Run the project                                                          
```
flask --app app run --debug
```

# Features & usage guideline

## Choose File & Submit

Download csv file format from Charles Proxy Server for your network session on which you wish to run the analysis. Once you select a csv file and click on submit, the file will get
uploaded and a csv file with the name as filtered_network_calls.csv will get generated. It contains all the ad network calls. The file can also be read in the project directory.

## Add Custom Filter & Delete Custom Filter

This feature allows you to add & delete custom domain names to allow custom filtering. The filtered data is created in a seprate csv file named as custom_filtered_network_calls.csv . This file contains all the network calls which were made to the user specified domain names. The file can also be read in the project directory. 
All the custom filters which have been added by the user will be displayed in the form of a table in the right side of the screen.

## Download Custom Filtered Network Calls .csv File

This feature saves the custom_filtered_network_calls.csv file in the download directory of the user's system.

## Download Filtered Network Calls .csv File

This feature saves the filtered_network_calls.csv file in the download directory of the user's system.

### Custom Filtered Network Calls

This radio button contains the filtered data based on the user provided filters if any.

### Filtered Network Calls

This radio button contains the filtered data based on the Ad Network filters.

### Network Calls

This radio button contains the original network calls data.


## Generate Graph Functionality

Based on the user selected radio button, if their is data generated initially, a graph renders on the screen after clicking of the "Generate Graph" button. 
If their are no custom filters added, clicking on the Custom Filtered Network Calls radio button and generating graph would not fetch any graph. The graph is interactive and the user
can pan and zoom and hover as required. A .jpg file of the graph would also get saved in the project directory after any selected graph is generated. Seperate .jpg file would get 
generated for all the different types of graph. 
All the 400 & 500 level status code will be displayed in red color in the graph.

## Download Graph Functionality

Based on the user selected radio button, if their is graph generated initially, a .jpg file of the graph gets download in the download directory after clicking of the "Download Graph" button.

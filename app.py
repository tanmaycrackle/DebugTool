from flask import Flask, render_template, request, flash, redirect, url_for, logging, send_file, jsonify
import plotly.graph_objs as go
import requests
import re
import os
import pandas as pd

app = Flask(__name__)

app.secret_key = 'your_secret_key'


UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def clear_data_on_startup():
    # Specify the files to be cleared
    files_to_clear = ['custom_filtered_network_calls.csv', 
                    'filtered_network_calls.csv', 
                    'easylist_objects.txt',
                    'additional_ssp_list.txt']

    # Specify the files to be deleted
    files_to_delete = ['filtered_network_graph.jpg', 
                    'custom_filtered_network_graph.jpg',
                    'network_graph.jpg']

    # Get the directory path where the app.py file is located
    current_dir = os.path.dirname(__file__)

    # Clear data from specified files
    for file_name in files_to_clear:
        file_path = os.path.join(current_dir, file_name)
        if os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.truncate(0)
                app.logger.info(f"Data cleared from file: {file_name}")
        else:
            app.logger.warning(f"File does not exist: {file_name}")

    # Delete specified files
    for file_name in files_to_delete:
        file_path = os.path.join(current_dir, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            app.logger.info(f"File deleted: {file_name}")
        else:
            app.logger.warning(f"File does not exist: {file_name}")


# Check if the application context is being initialized for the first time
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    clear_data_on_startup()


easylist_set = set()  # Global variable to store the EasyList set
charles_df = pd.DataFrame() # Global variable to the uploaded file 
filtered_network_calls_df = pd.DataFrame()  # Global variable to store filtered network calls

# New global variables for custom filtering
prebuilt_set = set()  # Global variable for set using custom filtering
custom_filtered_network_calls_df = pd.DataFrame() # Dataframe for storing data after custom filtering
file_path = 'additional_ssp_List.txt' # Path at which custom filters are being written
graph_name = '' # Variable being used for saving graphs


def load_file(file_path): # Function for loading main network call dataset after clicking on submit button
    global charles_df
    try:
        charles_df = pd.read_csv(file_path)
        return charles_df
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def generate_easy_list_set(): # Function for extracting names of ad network sites and storing in easylist_set
    easylist_url = "https://easylist.to/easylist/easylist.txt" # The site which contains all the ad sites
    easylist_response = requests.get(easylist_url)
    easylist_content = easylist_response.text

    # Extract matches directly into a set, considering '^', '&', or end of the line
    easylist_patterns = set(match.group(1) for match in re.finditer(r"^\|\|([^\^\$&]+)[\^\$&]?[^\S\n]*$", easylist_content, re.MULTILINE) if not match.group().startswith("@@||"))

    # Save the set to a file
    with open('easylist_objects.txt', 'w') as file:
        for obj in easylist_patterns:
            file.write(obj + '\n')

    return easylist_patterns


def generate_ad_network_output(): # Function being used to filter the main dataset for ad network calls
    global filtered_network_calls_df, charles_df
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))

    # Filter network calls based on EasyList patterns
    filtered_network_calls_df = charles_df[charles_df['URL'].apply(lambda url: any(substring in easylist_set for substring in generate_substrings(generate_substring_for_url(url))))]

    # Save the filtered network calls to a separate CSV file
    filtered_log_path = 'filtered_network_calls.csv'  # Adjust the desired path
    filtered_network_calls_df.to_csv(filtered_log_path, index=False)

    flash('Ad network output generated successfully.', 'success')
    return redirect(url_for('index'))


def extract_name(input_string): # Function being used to extract display name for calls being used in graph display
    # Find the first occurrence of "//"
    start_index = input_string.find("//")
    if start_index == -1:
        return None  # "//" not found in the input string
    
    # Find the next occurrence of "/"
    end_index = input_string.find("/", start_index + 2)
    if end_index == -1:
        # If "/" not found after "//", return the substring from "//" until the end
        extracted_substring = input_string[start_index + 2:]
    else:
        # Extract the substring between "//" and "/"
        extracted_substring = input_string[start_index + 2:end_index]
    
    return extracted_substring



def generate_substrings(input_str): # Function being used to search all substrings to check if the string has a matching common name with the prebuilt set
    return [input_str[i:j] for i in range(len(input_str)) for j in range(i + 1, len(input_str) + 1)]

def generate_substring_for_url(url): # Generating a short substring to search for 
    prefixes = ["https://", "http://"]
    endings = [".com", ".co.in", ".org", ".net"]  # Add more endings if needed

    for prefix in prefixes:
        if url.startswith(prefix):
            url = url[len(prefix):]
            break

    question_mark_index = url.find("?")

    if question_mark_index != -1:
        substring = url[:question_mark_index]
    else:
        for ending in endings:
            index = url.find(ending)
            if index != -1:
                substring = url[:index] + ending
                break
        else:
            substring = url

    return substring


def resetfilter(): # Function being called everytime a new custom filter is added or deleted
    global prebuilt_set, custom_filtered_network_calls_df, charles_df
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))
    
    if not prebuilt_set:
        # Empty the DataFrame by dropping all rows
        custom_filtered_network_calls_df = pd.DataFrame()
        log_path = 'custom_filtered_network_calls.csv'
        custom_filtered_network_calls_df.to_csv(log_path, index=False)
        return
    # Filter rows based on substring presence in the adblock regex set
    custom_filtered_network_calls_df = charles_df[charles_df['URL'].apply(lambda url: any(substring in prebuilt_set for substring in generate_substrings(generate_substring_for_url(url))))]
    log_path = 'custom_filtered_network_calls.csv'
    custom_filtered_network_calls_df.to_csv(log_path, index=False)
    # update_filters_table()  # Render table after addition
    return

def add_to_set_and_file(input_string): # Function being used add custom filter string
    global custom_filtered_network_calls_df
    if input_string not in prebuilt_set:
        global file_path
        prebuilt_set.add(input_string)
        with open(file_path, 'a') as file:
            file.write(input_string + '\n')
        resetfilter()
    return

def delete_from_set_and_file(input_string): # Function being used delete custom filter string
    global custom_filtered_network_calls_df
    if input_string in prebuilt_set:
        global file_path
        prebuilt_set.remove(input_string)
        with open(file_path, 'r') as file:
            lines = file.readlines()
        with open(file_path, 'w') as file:
            for line in lines:
                if line.strip() != input_string:
                    file.write(line)
        resetfilter()
    return


@app.route('/', methods=['GET', 'POST']) # Main entry point of the tool
def index():
    global filtered_network_calls_df, charles_df, easylist_set, custom_filtered_network_calls_df, prebuilt_set
    app.logger.debug("Hello world !!!!!!!!!!!!!!!!!!")
    if request.method == 'POST': # Below code being used to submit a csv file
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                if file.filename.endswith('.csv'):
                    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_file.csv')):
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_file.csv'))    
                    filename = 'uploaded_file.csv'
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    charles_df = load_file(file_path)
                    if charles_df is not None:
                        print(f"File '{file.filename}' has been uploaded successfully!")
                        filtered_network_calls_df = None
                        custom_filtered_network_calls_df = None
                        if not easylist_set: 
                            easylist_set = generate_easy_list_set()
                        generate_ad_network_output()
                    return redirect(url_for('index'))  
                else:
                    print("Only .csv files are accepted.")
    
    return render_template('index.html', filters=prebuilt_set)

# @app.route('/get_filters', methods=['GET'])
# def get_filters():
#     global prebuilt_set
#     filters = list(prebuilt_set) # Convert set to list
#     return jsonify(filters=filters) # Return filters as JSON


@app.route('/add_to_set_and_file', methods=['POST']) #Route to add custom filter
def add_to_set_and_file_route():
    global  prebuilt_set, charles_df
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))
    input_string = request.form.get('input_string')
    if len(input_string) == 0:
        flash('Error: Please enter a string', 'danger')
        return redirect(url_for('index'))
    lower_input_string = input_string.lower()
    add_to_set_and_file(lower_input_string)
    flash(f'Success: Added "{lower_input_string}" to the set and file.', 'success')
    return redirect(url_for('index'))

@app.route('/delete_from_set_and_file', methods=['POST']) #Route to delete custom filter
def delete_from_set_and_file_route():
    global  prebuilt_set, charles_df
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))
    input_string = request.form.get('input_string')
    if len(input_string) == 0:
        flash('Error: Please enter a string', 'danger')
        return redirect(url_for('index'))
    lower_input_string = input_string.lower()
    delete_from_set_and_file(lower_input_string)
    flash(f'Success: Deleted "{lower_input_string}" from the set and file.', 'success')
    return redirect(url_for('index'))

@app.route('/download_custom_filtered_network_calls') #Function being used to download specific file
def download_custom_filtered_network_calls():
    return send_file('custom_filtered_network_calls.csv', as_attachment=True)

@app.route('/download_filtered_network_calls') #Function being used to download specific file
def download_filtered_network_calls():
    return send_file('filtered_network_calls.csv', as_attachment=True)

@app.route('/download_graph', methods=['POST'])
def download_graph():
    graph_name = None
    if request.form.get('network_calls_df') == 'custom_filtered':   
        graph_name = 'custom_filtered_network_graph.jpg'
    elif request.form.get('network_calls_df') == 'filtered':
        graph_name = 'filtered_network_graph.jpg'
    elif request.form.get('network_calls_df') == 'network_calls':
        graph_name = 'network_graph.jpg'

    if os.path.isfile(graph_name):
        return send_file(graph_name, as_attachment=True)
    else:
        return redirect(url_for('index'))

@app.route('/generate_graph', methods=['POST']) #Function being used to generate graph
def generate_graph():
    global charles_df, custom_filtered_network_calls_df, filtered_network_calls_df,graph_name,prebuilt_set
    selected_df = None # Below lines to confirm the type of graph selected by the radio button
    if request.form.get('network_calls_df') == 'custom_filtered':
        selected_df = custom_filtered_network_calls_df
        graph_name = 'custom_filtered_network_graph.jpg'
    elif request.form.get('network_calls_df') == 'filtered':
        selected_df = filtered_network_calls_df
        graph_name = 'filtered_network_graph.jpg'
    elif request.form.get('network_calls_df') == 'network_calls':
        selected_df = charles_df
        graph_name = 'network_graph.jpg'

    if selected_df is None or selected_df.empty : 
        return redirect(url_for('index'))

    # Generate information table with selected parameters
    testdf = selected_df[['URL','Status','Response Code','Method',
                          'Request Start Time','Request End Time',
                          'Response Start Time','Response End Time',
                          'Duration (ms)', 'DNS Duration (ms)',
                          'Connect Duration (ms)', 'SSL Duration (ms)',
                          'Request Duration (ms)', 'Response Duration (ms)',
                          'Latency (ms)']].copy()
    testdf = testdf.reset_index(drop=True)

    testdf['Request Start Time'] = pd.to_datetime(testdf['Request Start Time'], format='%y/%m/%d %H:%M')

    # Create a column with shortened URLs for better display
    testdf['Shortened URL'] = testdf['URL'].apply(extract_name)

    # Create an empty list to store individual traces
    traces = []

    # Iterate through each row in the DataFrame and create traces for Request, Response, and Latency
    for index, row in testdf.iterrows():
        req_color = 'rgba(214, 114, 237, 0.8)'
        latency_color = 'rgba(255, 165, 0, 0.7)'
        res_color = 'rgba(76, 140, 237, 0.8)'
        if row['Response Code'] // 100 == 4 or row['Response Code'] // 100 == 5:
            req_color = 'rgba(255, 0, 0, 0.8)'
            latency_color = 'rgba(255, 0, 0, 0.8)'
            res_color = 'rgba(255, 0, 0, 0.8)'
        request_trace = go.Bar(
            y=[index],
            x=[row['Request Duration (ms)']], # Mutiplying it by a factor since the request duration is very small in number
            orientation="h",
            name=f"Request - {row['Shortened URL']}",
            hoverinfo="text",
            text=f"URL: {row['Shortened URL']}<br>Time: {row['Request Start Time']} ms<br>Request Duration: {row['Request Duration (ms)']} ms<br>Code: {row['Response Code']}",
            # showlegend=True,
            marker=dict(color=req_color, line=dict(width=0.01, color='black'))
        )

        latency_trace = go.Bar(
            y=[index],
            x=[row['Latency (ms)']],
            orientation="h",
            name=f"Latency - {row['Shortened URL']}",
            hoverinfo="text",
            text=f"URL: {row['Shortened URL']}<br>Time: {row['Request Start Time']} ms<br>Latency: {row['Latency (ms)']} ms<br>Code: {row['Response Code']}",
            # showlegend=True,
            marker=dict(color=latency_color, line=dict(width=0.01, color='black'))
        )

        response_trace = go.Bar(
            y=[index],
            x=[row['Response Duration (ms)']], # Mutiplying it by a factor since the response duration is very small in number
            orientation="h",
            name=f"Response - {row['Shortened URL']}",
            hoverinfo="text",
            text=f"URL: {row['Shortened URL']}<br>Time: {row['Request Start Time']} ms<br>Response: {row['Response Duration (ms)']} ms<br>Code: {row['Response Code']}",
            # showlegend=True,
            marker=dict(color=res_color, line=dict(width=0.01, color='black'))
        )

        traces.extend([request_trace, latency_trace, response_trace])

    # Create layout
    layout = go.Layout(
        title="Network Waterfall Chart",
        yaxis=dict(title="Index"), 
        xaxis=dict(title="Time", range=[0, max(testdf['Request Duration (ms)'])]),
        barmode='stack',
        height=800,  # Adjusted height to accommodate more bars
        width=800,
        showlegend=False,
        hovermode='closest',
        annotations=[
            # Add custom legends as annotations
            dict(x=1.05, y=0.9, xref='paper', yref='paper',
                text='Request Duration', showarrow=False,
                font=dict(size=12, color='rgba(214, 114, 237, 0.8)')),

            dict(x=1.05, y=0.8, xref='paper', yref='paper',
                text='Latency', showarrow=False,
                font=dict(size=12, color='rgba(255, 165, 0, 0.7)')),

            dict(x=1.05, y=0.7, xref='paper', yref='paper',
                text='Response Duration', showarrow=False,
                font=dict(size=12, color='rgba(76, 140, 237, 0.8)'))
        ]
    )

    # Create figure
    fig = go.Figure(data=traces, layout=layout)

    # Save the figure as JPG file
    fig.write_image(graph_name)

    # Render template with the graph
    return render_template('index.html', graph=fig.to_html(),filters=prebuilt_set)


if __name__ == '__main__':
    app.run(debug=True)

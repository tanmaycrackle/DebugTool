from flask import Flask, render_template, request, flash, redirect, url_for, logging, send_file
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

easylist_set = set()  # Global variable to store the EasyList set
charles_df = pd.DataFrame() # Global variable to the uploaded file 
filtered_network_calls_df = pd.DataFrame()  # Global variable to store filtered network calls

# New global variables for custom filtering
prebuilt_set = set()  # Replace this with your prebuilt set
# custom_save_path = 'additional_ssp_list.txt'  # File where results are being compiled after being filtered
custom_filtered_network_calls_df = pd.DataFrame()
file_path = 'additional_ssp_List.txt'
graph_name = ''

def load_file(file_path):
    global charles_df
    try:
        charles_df = pd.read_csv(file_path)
        return charles_df
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def generate_easy_list_set():
    easylist_url = "https://easylist.to/easylist/easylist.txt"
    easylist_response = requests.get(easylist_url)
    easylist_content = easylist_response.text

    # Extract matches directly into a set, considering '^', '&', or end of the line
    easylist_patterns = set(match.group(1) for match in re.finditer(r"^\|\|([^\^\$&]+)[\^\$&]?[^\S\n]*$", easylist_content, re.MULTILINE) if not match.group().startswith("@@||"))

    # Save the set to a file
    with open('easylist_objects.txt', 'w') as file:
        for obj in easylist_patterns:
            file.write(obj + '\n')

    return easylist_patterns


def generate_ad_network_output():
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

def generate_substrings(input_str):
    return [input_str[i:j] for i in range(len(input_str)) for j in range(i + 1, len(input_str) + 1)]

def generate_substring_for_url(url):
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

def resetfilter():
    global prebuilt_set, custom_filtered_network_calls_df, charles_df
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))
    # app.logger.debug(charles_df.columns)
    if not prebuilt_set:
        # Empty the DataFrame by dropping all rows
        custom_filtered_network_calls_df = pd.DataFrame(columns = charles_df.columns)
        log_path = 'custom_filtered_network_calls.csv'
        custom_filtered_network_calls_df.to_csv(log_path, index=False)
        return
    # Filter rows based on substring presence in the adblock regex set
    custom_filtered_network_calls_df = charles_df[charles_df['URL'].apply(lambda url: any(substring in prebuilt_set for substring in generate_substrings(generate_substring_for_url(url))))]
    log_path = 'custom_filtered_network_calls.csv'
    custom_filtered_network_calls_df.to_csv(log_path, index=False)
    return

def add_to_set_and_file(input_string):
    app.logger.debug(f"before addition Global Data: {prebuilt_set}")
    global custom_filtered_network_calls_df
    if input_string not in prebuilt_set:
        global file_path
        prebuilt_set.add(input_string)
        with open(file_path, 'a') as file:
            file.write(input_string + '\n')
        resetfilter()
        app.logger.debug(f"After addition Global Data: {prebuilt_set}")
    return

def delete_from_set_and_file(input_string):
    app.logger.debug(f"Before deletion Global Data: {prebuilt_set}")
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
        app.logger.debug(f"After deletion Global Data: {prebuilt_set}")
    return


@app.route('/', methods=['GET', 'POST'])
def index():
    # file_path, custom_filtered_network_calls_df, filtered_network_calls_df, prebuilt_set, easylist_set
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                global charles_df,easylist_set
                charles_df = load_file(file_path)
                if charles_df is not None:
                    print(f"File '{file.filename}' has been uploaded successfully!")
                easylist_set = generate_easy_list_set()

    return render_template('index.html')

# @app.route('/generate_easy_list', methods=['POST'])
# def generate_easy_list():
#     global easylist_set
#     easylist_set = generate_easy_list_set()
#     flash('Operation successful', 'success')
#     return redirect(url_for('index'))  # Redirect to the home directory


@app.route('/generate_ad_network_output', methods=['POST'])
def generate_ad_network_output_route():
    return generate_ad_network_output()


@app.route('/add_to_set_and_file', methods=['POST'])
def add_to_set_and_file_route():
    global  prebuilt_set, charles_df
    app.logger.debug(f"Set initially : {prebuilt_set}")
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

@app.route('/delete_from_set_and_file', methods=['POST'])
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

@app.route('/download_custom_filtered_network_calls')
def download_custom_filtered_network_calls():
    return send_file('custom_filtered_network_calls.csv', as_attachment=True)

@app.route('/download_filtered_network_calls')
def download_filtered_network_calls():
    return send_file('filtered_network_calls.csv', as_attachment=True)




@app.route('/generate_graph', methods=['POST'])
def generate_graph():
    global charles_df, custom_filtered_network_calls_df, filtered_network_calls_df,graph_name
    # Get the selected dataframe from the radio button
    selected_df = None
    if request.form.get('network_calls_df') == 'custom_filtered':
        selected_df = custom_filtered_network_calls_df
        graph_name = 'custom_filtered_network_graph.jpg'
    elif request.form.get('network_calls_df') == 'filtered':
        selected_df = filtered_network_calls_df
        graph_name = 'filtered_network_graph.jpg'
    elif request.form.get('network_calls_df') == 'network_calls':
        selected_df = charles_df
        graph_name = 'network_graph.jpg'

    # Check if the selected dataframe has changed from its previous state
    # if selected_df.equals(generate_graph.last_df):
    #     return "No changes detected. Graph not generated."

    # Generate information table
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
    testdf['Shortened URL'] = testdf['URL'].apply(lambda x: x[:12] + '...' if len(x) > 13 else x)

    # Create an empty list to store individual traces
    traces = []

    # Iterate through each row in the DataFrame and create traces for Request, Response, and Latency
    for index, row in testdf.iterrows():
        request_trace = go.Bar(
            y=[index],
            x=[row['Request Duration (ms)'] * 100], # Mutiplying it by a factor since the request duration is very small in number
            orientation="h",
            name=f"Request - {row['Shortened URL']}",
            hoverinfo="x+text",
            text=f"URL: {row['Shortened URL']}<br>Time: {row['Request Start Time']} ms<br>Request Duration: {row['Request Duration (ms)']} ms<br>Code: {row['Response Code']}",
            # showlegend=True,
            marker=dict(color='rgba(214, 114, 237, 0.8)', line=dict(width=0))
        )

        latency_trace = go.Bar(
            y=[index],
            x=[row['Latency (ms)']],
            orientation="h",
            name=f"Latency - {row['Shortened URL']}",
            hoverinfo="x+text",
            text=f"URL: {row['Shortened URL']}<br>Time: {row['Request Start Time']} ms<br>Latency: {row['Latency (ms)']} ms<br>Code: {row['Response Code']}",
            # showlegend=True,
            marker=dict(color='rgba(255, 165, 0, 0.7)', line=dict(width=0))
        )

        response_trace = go.Bar(
            y=[index],
            x=[row['Response Duration (ms)'] * 100], # Mutiplying it by a factor since the response duration is very small in number
            orientation="h",
            name=f"Response - {row['Shortened URL']}",
            hoverinfo="x+text",
            text=f"URL: {row['Shortened URL']}<br>Time: {row['Request Start Time']} ms<br>Response: {row['Response Duration (ms)']} ms<br>Code: {row['Response Code']}",
            # showlegend=True,
            marker=dict(color='rgba(76, 140, 237, 0.8)', line=dict(width=0))
        )

        traces.extend([request_trace, latency_trace, response_trace])

    # Create layout
    layout = go.Layout(
        title="Network Waterfall Chart",
        yaxis=dict(title="Index"), 
        xaxis=dict(title="Time"),
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
    
    # Show the figure
    # fig.show()

    # Save the figure as JPG file
    fig.write_image(graph_name)

    # Update the last dataframe with the current selected dataframe
    # generate_graph.last_df = selected_df.copy()

    # Render template with the graph
    return render_template('index.html', graph=fig.to_html())

# Initialize the last dataframe as None
# generate_graph.last_df = None



if __name__ == '__main__':
    app.run(debug=True)

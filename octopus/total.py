import sys, os, requests, json
from datetime import datetime, time, timedelta
from configobj import ConfigObj

script_path = os.path.dirname(os.path.realpath(__file__))
settings = ConfigObj(script_path+"/agile.conf", file_error=True)

# Octopus request parameters
params = {'page':1,'order_by':'period','page_size':25000}

total = 0
from_time = 0

# Step 1: Create feed via API call or use input interface in emoncms to create manually
result = requests.get(settings['emoncms']['server']+"/feed/getid.json",params={'tag':'agile','name':'consumption_total','apikey':settings['emoncms']['apikey']})
if not result.text:
    # Create feed
    params = {'tag':'agile','name':'consumption_total','datatype':1,'engine':5,'options':'{"interval":1800}','unit':'kWh','apikey':settings['emoncms']['apikey']}
    result = requests.get(settings['emoncms']['server']+"/feed/create.json",params)
    result = json.loads(result.text)
    if result['success']:
        feedid = int(result['feedid'])
        print("Emoncms feed created:\t"+str(feedid))
    else:
        print("Error creating feed")
        sys.exit(0)
else:
    feedid = int(result.text)
    print("Using emoncms feed:\t"+str(feedid))
    
    # Step 2: if feed exists, then attempt to fetch the value from 10 days ago
    midnight = datetime.combine(datetime.today(), time.min)
    from_time = midnight - timedelta(days=5)
    
    result = requests.get(settings['emoncms']['server']+"/feed/value.json",params={'id':feedid,'time':int(from_time.timestamp()),'apikey':settings['emoncms']['apikey']})
    value = json.loads(result.text)
    print("Feed meta data:\t\t"+result.text)

    if value:
        total = value
        params['period_from'] = from_time.astimezone().isoformat()
        print("Start: "+params['period_from']+' => '+str(total)+' kWh')

# Step 3: Request history from Octopus
url = "https://api.octopus.energy/v1/electricity-meter-points/%s/meters/%s/consumption/" % (settings['octopus']['mpan'],settings['octopus']['serial_number'])
result = requests.get(url,params=params,auth=(settings['octopus']['agile_apikey'],''))
data = json.loads(result.text)

if not data: sys.exit(0)
if not 'results' in data: sys.exit(0)

dp_received = len(data['results'])
print("Number of data points:\t%s" % dp_received);

# Step 4: Process history into data array for emoncms
data_out = []
for dp in data['results']:
    time = int(datetime.timestamp(datetime.strptime(dp['interval_end'],"%Y-%m-%dT%H:%M:%S%z")))
    total += dp['consumption']
    data_out.append([time,total])
print("End: "+dp['interval_end']+" => "+str(total)+' kWh')

# Step 5: Send data to emoncms
if len(data_out):
    print("Posting data to emoncms")
    result = requests.post(settings['emoncms']['server']+"/feed/insert.json",params={'id':feedid,'apikey':settings['emoncms']['apikey'],'skipbuffer':1},data={'data':json.dumps(data_out)})


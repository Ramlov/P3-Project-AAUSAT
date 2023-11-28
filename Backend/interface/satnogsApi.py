import requests

def get_satellites_list():
    api_url = "https://db.satnogs.org/api/satellites/"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for bad responses

        satellites_list = response.json()
        sat_list = []
        if satellites_list:
            for satellite in satellites_list:
                # print(f"Satellite Name: {satellite['name']}")
                sat_name = satellite['name']
                sat_list.append(sat_name)
                # print(f"Satellite NORAD ID: {satellite['norad_cat_id']}")
            # print(sat_list)
        else:
            print("Failed to retrieve the list of satellites.")   
        return sat_list
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None
    
# def get_satellite_data(satellite_id):
#     api_url = f"https://db.satnogs.org/api/satellite/{satellite_id}/"
    
#     try:
#         response = requests.get(api_url)
#         response.raise_for_status()  # Raise an exception for bad responses

#         data = response.json()
#         return data
#     except requests.exceptions.RequestException as e:
#         print(f"Error: {e}")
#         return None
    
 # Fetch TLE data from Celestrak for AAUSAT-2
def get_celestrak_tle():
    # Replace 'tle_AAUSAT2' with the actual URL for AAUSAT-2 TLE data
    tle_AAUSAT2_url = 'http://celestrak.org/NORAD/elements/gp.php?CATNR=32788&FORMAT=tle'
    response = requests.get(tle_AAUSAT2_url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Print the TLE data
        print(response.text)
    else:
        print(f"Failed to fetch TLE data. Status code: {response.status_code}")

if __name__ == "__main__":
    get_celestrak_tle()

    # satellites_list = get_satellites_list()

    # if satellites_list:
    #     print("List of Satellites:")
    #     for satellite in satellites_list:
    #         print(f"Satellite Name: {satellite['name']}")
    #         print(f"Satellite NORAD ID: {satellite['norad_cat_id']}")
    #         # Add more fields as needed
    #         print("----------------------")
    # else:
    #     print("Failed to retrieve the list of satellites.")

    # # Replace '1234' with the actual satellite ID you want to query
    # satellite_id = 
    # satellite_data = get_satellite_data(satellite_id)

    # if satellite_data:
    #     print(f"Satellite Name: {satellite_data['name']}")
    #     print(f"Satellite NORAD ID: {satellite_data['norad_cat_id']}")
    #     # Add more fields as needed
    # else:
    #     print("Failed to retrieve satellite data.")
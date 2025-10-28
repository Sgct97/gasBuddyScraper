import csv
from datetime import datetime

def write_stations_to_csv(stations, csv_filename):
    """Append stations to CSV file incrementally"""
    file_exists = False
    try:
        with open(csv_filename, 'r'):
            file_exists = True
    except FileNotFoundError:
        pass
    
    fieldnames = [
        'station_id', 'station_name', 'brand', 
        'address_line1', 'city', 'state', 'zip',
        'latitude', 'longitude',
        'regular_cash_price', 'regular_cash_posted_time', 'regular_cash_reporter',
        'regular_credit_price', 'regular_credit_posted_time', 'regular_credit_reporter',
        'midgrade_cash_price', 'midgrade_credit_price',
        'premium_cash_price', 'premium_credit_price',
        'diesel_cash_price', 'diesel_credit_price',
        'has_convenience_store', 'has_car_wash', 'has_restrooms',
        'accepts_credit_cards', 'rating',
        'scraped_at'
    ]
    
    with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header only if file is new
        if not file_exists:
            writer.writeheader()
        
        scrape_timestamp = datetime.now().isoformat()
        
        for station in stations:
            address = station.get('address', {})
            prices_by_type = {}
            if 'prices' in station and station['prices']:
                for price_report in station['prices']:
                    fuel_type = price_report.get('fuelProduct', '')
                    cash_info = price_report.get('cash', {})
                    credit_info = price_report.get('credit', {})
                    
                    prices_by_type[fuel_type] = {
                        'cash_price': cash_info.get('price') if cash_info else None,
                        'cash_time': cash_info.get('postedTime') if cash_info else None,
                        'cash_reporter': cash_info.get('nickname') if cash_info else None,
                        'credit_price': credit_info.get('price') if credit_info else None,
                        'credit_time': credit_info.get('postedTime') if credit_info else None,
                        'credit_reporter': credit_info.get('nickname') if credit_info else None,
                    }
            
            amenities = station.get('amenities', {})
            
            row = {
                'station_id': station.get('id', ''),
                'station_name': station.get('name', ''),
                'brand': station.get('brand', {}).get('name', '') if station.get('brand') else '',
                'address_line1': address.get('line1', ''),
                'city': address.get('locality', ''),
                'state': address.get('region', ''),
                'zip': address.get('postalCode', ''),
                'latitude': address.get('latitude', ''),
                'longitude': address.get('longitude', ''),
                'regular_cash_price': prices_by_type.get('regular_gas', {}).get('cash_price', ''),
                'regular_cash_posted_time': prices_by_type.get('regular_gas', {}).get('cash_time', ''),
                'regular_cash_reporter': prices_by_type.get('regular_gas', {}).get('cash_reporter', ''),
                'regular_credit_price': prices_by_type.get('regular_gas', {}).get('credit_price', ''),
                'regular_credit_posted_time': prices_by_type.get('regular_gas', {}).get('credit_time', ''),
                'regular_credit_reporter': prices_by_type.get('regular_gas', {}).get('credit_reporter', ''),
                'midgrade_cash_price': prices_by_type.get('midgrade', {}).get('cash_price', ''),
                'midgrade_credit_price': prices_by_type.get('midgrade', {}).get('credit_price', ''),
                'premium_cash_price': prices_by_type.get('premium', {}).get('cash_price', ''),
                'premium_credit_price': prices_by_type.get('premium', {}).get('credit_price', ''),
                'diesel_cash_price': prices_by_type.get('diesel', {}).get('cash_price', ''),
                'diesel_credit_price': prices_by_type.get('diesel', {}).get('credit_price', ''),
                'has_convenience_store': amenities.get('hasConvenienceStore', ''),
                'has_car_wash': amenities.get('hasCarWash', ''),
                'has_restrooms': amenities.get('hasRestrooms', ''),
                'accepts_credit_cards': amenities.get('acceptsCreditCards', ''),
                'rating': station.get('starRating', ''),
                'scraped_at': scrape_timestamp
            }
            
            writer.writerow(row)

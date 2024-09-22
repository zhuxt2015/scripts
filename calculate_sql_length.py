import gzip
import glob
import re
import os

def calculate_sql_lengths(log_file):
    sql_lengths = []
    
    # Open gzip file and read content
    with gzip.open(log_file, 'rb') as f:
        content = f.read()
    
    # Find all SQL queries in the log file
    sql_matches = re.finditer(r'sql:\n(.*?)(?:\.\.\.and (\d+) characters more|\n\n)', content, re.DOTALL)
    
    for match in sql_matches:
        visible_sql = match.group(1)
        remaining_chars = int(match.group(2)) if match.group(2) else 0
        
        total_length = len(visible_sql.decode("utf-8")) + remaining_chars
        sql_lengths.append(total_length)
    
    return sql_lengths

# Directory containing the log files
log_dir = '/app/tomcat/logs'  # Replace with actual directory path

# Get all .gz files matching the pattern
log_files = glob.glob(os.path.join(log_dir, 'fanruan.log.*.gz'))

max_length = 0
max_length_file = ''

for log_file in log_files:
    print "Processing file: {}".format(log_file)
    lengths = calculate_sql_lengths(log_file)
    
    if lengths:
        file_max_length = max(lengths)
        if file_max_length > max_length:
            max_length = file_max_length
            max_length_file = log_file
        
        print "  Found {} SQL queries.".format(len(lengths))
        print "  Maximum SQL length in this file: {} characters".format(file_max_length)
    else:
        print "  No SQL queries found in this file."

if max_length > 0:
    print "\nOverall maximum SQL length: {} characters".format(max_length)
    print "Found in file: {}".format(max_length_file)
else:
    print "\nNo SQL queries found in any of the processed files."
STRING       = 0       # Single-line plain text (default)
TEXT         = 1       # Multiline text. 'syntax' can be provided in config
INTEGER      = 2       # Integer only value (for db keys etc)
NUMERIC      = 3       # Any integer of float number. 'min', 'max' and 'step' values can be provided in config
BOOLEAN      = 4       # 1/0 checkbox
DATETIME     = 5       # Date and time information. Stored as timestamp
TIMECODE     = 6       # Timecode information, stored as float(seconds), presented as HH:MM:SS:FF or HH:MM:SS.CS (centiseconds)
REGIONS      = 7       # List of regions
FRACTION     = 8       # 16/9 etc...
SELECT       = 9       # Select one value from list. stored as string or int value
LIST         = 10      # Select 0 or more values from list, stored as array
COLOR        = 11      # stored as integer

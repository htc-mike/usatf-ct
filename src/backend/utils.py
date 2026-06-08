"""Shared utility functions for the HTC results pipeline."""
import data_db as data
df_age_grade = data.get_age_grade_data()

def millis_to_time(millis: int) -> str:
    """Convert milliseconds to a time string.

    Returns ``HH:MM:SS.ms`` when hours > 0, otherwise ``MM:SS.ms``.
    The millisecond component is zero-padded to three digits.

    Args:
        millis: Total elapsed time in milliseconds.

    Returns:
        Formatted time string, e.g. ``"1:13:14.352"`` or ``"4:59.500"``.
    """
    if millis < 0:
        millis = 0

    total_seconds, ms = divmod(millis, 1000)
    total_minutes, secs = divmod(total_seconds, 60)
    hours, mins = divmod(total_minutes, 60)

    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"

def time_to_millis(time:str) -> int:
    hours = 0
    mins = 0
    secs = 0
    time_array = time.split(':')
    time_array_length = len(time_array)
    if time_array_length == 3:
        hours = int(time_array[0]) * 60 * 60 
        mins = int(time_array[1]) * 60 
        secs = int(time_array[2]) 
    elif time_array_length == 2:
        mins = int(time_array[0]) * 60 
        secs = int(time_array[1]) 
    return (hours + mins + secs) * 1000

def get_age_grade(sex, age, dist_mi, time_in_millis):
    
    if sex != '':
        dist_mi_column = "_" + "{:.2f}".format(float(dist_mi)).replace(".", "_")

        try:
            df = df_age_grade.loc[(df_age_grade['sex'] == sex) & (df_age_grade['age'] == age), dist_mi_column]
            if len(df.values)>0:
                age_grade_secs = df.values[0]
                age_grade_percent = (age_grade_secs/(time_in_millis/1000))*100
                age_grade_percent_format = "{:.2f}%".format(age_grade_percent)
            else:
                age_grade_percent_format = '00.00%'
        except:
            age_grade_percent_format = '00.00%'
    else:
        age_grade_percent_format = '00.00%'

    return age_grade_percent_format

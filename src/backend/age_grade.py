import data

df_age_grade = data.get_age_grade_data()

def main():

    print(df_age_grade.head())

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

if __name__ == '__main__':
    main()
from datetime import timedelta

def get_right_time_word(time_left, time_left_type):
    results = "{} ".format(time_left)
    if time_left_type == 'hours':
        if time_left % 10 == 1 and (time_left // 10) != 1:
            results += 'час'
        elif (time_left % 10) in [2, 3, 4] and (time_left // 10) != 1:
            results += 'часа'
        else:
            results += 'часов'
    elif time_left_type == 'minutes':
        if time_left % 10 == 1 and (time_left // 10) != 1:
            results += 'минуту'
        elif (time_left % 10) in [2, 3, 4] and (time_left // 10) != 1:
            results += 'минуты'
        else:
            results += 'минут'
    return results


def get_time_ago_words(diff: timedelta):
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 60:
            return "только что"
        if second_diff < 120:
            return "минуту назад"
        if second_diff < 3600:
            minutes_diff = int(second_diff / 60)
            if minutes_diff % 10 == 1 and minutes_diff // 10 != 1:
                return str(int(second_diff / 60)) + " минуту назад"
            if minutes_diff % 10 in [2, 3, 4] and minutes_diff // 10 != 1:
                return str(int(second_diff / 60)) + " минуты назад"
            return str(int(second_diff / 60)) + " минут назад"
        if second_diff < 7200:
            return "час назад"
        if second_diff < 86400:
            hours_diff = second_diff // 3600
            if hours_diff % 10 == 1 and hours_diff // 10 != 1:
                return str(hours_diff) + " час назад"
            if hours_diff % 10 in [2, 3, 4] and hours_diff // 10 != 1:
                return str(hours_diff) + " часа назад"
            return str(hours_diff) + " часов назад"
    if day_diff == 1:
        return "вчера"
    if day_diff < 7:
        if int(day_diff) < 5:
            return str(int(day_diff)) + " дня назад"
        else:
            return str(int(day_diff)) + " дней назад"
    if day_diff < 14:
        return "неделю назад"
    if day_diff < 31:
        return str(int(day_diff / 7)) + " недели назад"
    if day_diff < 365:
        return str(int(day_diff / 30)) + " месяцев назад"
    if day_diff < 365 * 2:
        return "год назад"
    if day_diff < 365 * 5:
        return str(int(day_diff / 365)) + " года назад"
    return str(day_diff / 365) + " лет назад"
    results = "{} ".format(time_left)

"""
File to declare choices of different fields
"""

LIKE = 1
DISLIKE = 0

SCORE_CHOICES = [
    (LIKE, 'Like'),
    (DISLIKE, 'Dislike'),
]

APPROVED = 1
ON_REVIEW = 0
REJECTED = -1

CHECKED_CHOICES = [
    (APPROVED, 'Approved'),
    (ON_REVIEW, 'On review'),
    (REJECTED, 'Rejected'),
]

USER_BASED = 0
ITEM_BASED = 1
RANDOM_RECOMMEND = 2
AUTHOR_LIKE = 3
RECOMMEND_START = 4
ORIGIN_BASED = 5
MEME_OF_THE_DAY = 6
TOP_DAY_BASED = 7
N_LAST_DAYS_RANDOM = 8
RECOMMEND_ERROR = -1
TOP_BASED = 9

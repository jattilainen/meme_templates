# Getters and setters documentation #

## Import ##
Source code for getters: `django_backend/memeapp/getters.py`
Setters: `django_backend/memeapp/setters.py`

Since recommendation system is a part of django backend,
getters and setters can be imported as a part of a project, like this:
`from memeapp.getters import get_user_history`

## Functions description ##

### get_users_embeddings(users_ids) ###
**Input**: list or numpy.array of users_ids

**Output**: list of embeddings

NOTE: list is returned even if len(users_ids) == 1

### get_memes_embeddings(memes_ids) ###
Same for memes

### get_user_history(user_id, n, liked, embeddings, ratings) ###
**Input**: user_id: int (required);

n: int (default=-1);

liked: boolean (default: False);

embeddings: boolean (default:False);

ratings: boolean (default: False);

**Output**: np.array of last interacted / liked memes ids,
embeddings (if required), ratings (if required). If n=-1 all history is returned, otherwise all arrays contain n elements

## get_memes_history(meme_id, n, liked, embeddings, ratings) ##
Same for memes

## get_user_like_history(user_id, n) ##
**Input**: user_id: int (required);

n: int (default=-1)

**Output**: tuple(np.array(ids), np.array(embeddings))

Returns memes liked by user and their embeddings

## get_meme_like_history(meme_id, n) ##

Same for memes

## get_user_interact_history(user_id, n) ##
**Input**: user_id: int (required);

n: int (default=-1)

**Output**: tuple(np.array(ids), np.array(embeddings), np.array(ratings))

Returns memes user interacted with, their embeddings and scores

## get_meme_interact_history(meme_id, n) ##
Same for memes

## get_random_memes(n, embeddings) ##
**Input**: n: int (required); 

embeddings: boolean (default=False)

**Output**:

if embeddings=True return tuple(np.array(ids), np.array(embeddings))

else return np.array(ids)

## get_random_users(n, embeddings) ##
Same for users

## have_user_seen_memes(user_id, memes_ids) ##
**Input**: user_id: int (required)

memes_ids: array of int (required)

**Output**: boolean array of same length as memes_ids

## set_user_embedding(user_id, user_embedding) ##
**Input**: user_id: int (required)
user_embedding: np.array (required)

Sets user embedding

## set_meme_embedding(meme_id, meme_embedding) ##
Same for meme
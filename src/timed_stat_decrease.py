from datetime import datetime

BLOCK_HRS_TO_SEC = 6 * 3600

def timed_stat_decrease(last_updated_utc, current_time_utc):
	last_decrease_block = int(last_updated_utc.timestamp() // BLOCK_HRS_TO_SEC)
	current_decrease_block = int(current_time_utc.timestamp() // BLOCK_HRS_TO_SEC)

	# how many 6hr blocks have passed since last check
	block_difference = current_decrease_block - last_decrease_block

	return min(4, max(0, block_difference)) * 25

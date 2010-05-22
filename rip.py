import os
import sys
import threading
import time

import CDDB, DiscID

#TODO:
# Python bindings for lame
# Python bindings for cdparanoia
# Fetch CD Cover art
# See if there is another, similarly named dest dir already existing


def disk_data(disc_info, num):
	s = disc_info['DTITLE']
	artist = s.split(' / ')[0]
	album = s.split(' / ')[1]

	year = disc_info['DYEAR']
	genre = disc_info['DGENRE']

	track_title = disc_info['TTITLE' + `num-1`]
	track_name = "%s - %.02d %s" %(artist, num, track_title)
	track_name = track_name.replace(' ', '_')

	return artist, album, track_title, track_name, year, genre
	

#This function adds a dep for lame
def lame_thread(disc_info, num, cleanup):
	print "encoding track %d" %num

	(artist, album, track_title, track_name, year, genre) = disk_data(disc_info, num)

	lame_opts = "-S --preset extreme -q 0 -V 0"

	error = os.system('lame %s "%s.wav" "%s.mp3" --tt "%s" --ta "%s" --tl "%s" --ty "%s" --tn "%s" --tg "%s"'
			  %(lame_opts, track_name, track_name, track_title, artist, album, year, num, genre))
	if error:
		print "Error %d encounterd while encoding" %error

	if cleanup:
		os.system('rm "%s.wav"' %track_name)
	print "done encoding track %d" %num


#This function adds a dep for cdparanoia
def rip(device, disc_info, track):

	(artist, album, track_title, track_name, year, genre) = disk_data(disc_info, track)

	error = os.system('cdparanoia -wd %s %d "%s.wav"' %(device, track, track_name))
	if error:
		return -1

	return 0


def rip_encode(device, disc_info, track_count, cleanup):
	print "ripping & encoding"

	for i in range(track_count):
		error = rip(device, disc_info, i+1)
		if error:
			return -1

		lt = threading.Thread(target=lame_thread, args=(disc_info, i+1, cleanup))
		lt.start()

	return 0


def create_dest_dir(dest_dir, disc_info):
	print "creating dir"

	(artist, album, track_title, track_name, year, genre) = disk_data(disc_info, 1)
	artist = artist.replace(' ', '_')
	album = album.replace(' ', '_')

	error = os.chdir(dest_dir)
	if error:
		return -1

	error = os.access(artist, os.F_OK)
	if error == False:
		error = os.mkdir(artist)
		if error:
			return -1

	error = os.chdir(artist)
	if error:
		return -1

	error = os.access(album, os.F_OK)
	if error == False:
		error = os.mkdir(album)
		if error:
			return -1

	error = os.chdir(album)
	if error:
		return -1

	return 0


def create_playlist(dest_dir, disc_info, track_count):
	print "creating playlist"

	error = os.chdir(dest_dir)
	if error:
		return -1

	(artist, album, track_title, track_name, year, genre) = disk_data(disc_info, 1)
	artist = artist.replace(' ', '_')
	album = album.replace(' ', '_')

	m3u = open('%s_-_%s.m3u' %(artist, album), "w")

	for i in range(track_count):
		(artist, album, track_title, track_name, year, genre) = disk_data(disc_info, i+1)
		artist = artist.replace(' ', '_')
		album = album.replace(' ', '_')
		s = "%s/%s/%s\n" %(artist, album, track_name)
		m3u.writelines(s)

	m3u.close()

	return 0


#This function adds a dep for CDDB-py
def fetch_cd_info(device):
	print "fetching"

	cdrom = DiscID.open(device, 0)
	disc_id = DiscID.disc_id(cdrom)

	(query_status, query_info) = CDDB.query(disc_id)
	if query_status != 200:
		print "Error encountered querying CDDB, error = %d" %query_status
		return -1, None, 0

	(read_status, read_info) = CDDB.read(query_info['category'], query_info['disc_id'])
	if read_status != 210:
		print "Error encountered reading CDDB, error = %d" %read_status
		return -1, None, 0

	print read_info['DTITLE']
	print read_info['DYEAR']
	print read_info['DGENRE']
        for i in range(disc_id[1]):
	    print "Track %.02d: %s" %(i, read_info['TTITLE' + `i`])

	return 0, read_info, i+1


def parse_cmdline(args):

	cdrom = "/dev/cdrom"
	dest_dir = os.environ['HOME']
	cleanup = True

	for i in range(len(args)):
		if args[i] == "--device":
			cdrom = args[i+1] 
		if args[i] == "--dest_dir":
			dest_dir = args[i+1]
		if args[i] == "--nocleanup":
			cleanup = False	

	(rc, disc_info, track_count) = fetch_cd_info(cdrom)
	if rc:
		return

	rc = create_playlist(dest_dir, disc_info, track_count)
	if rc:
		return

	rc = create_dest_dir(dest_dir, disc_info)
	if rc:
		return

	rc = rip_encode(cdrom, disc_info, track_count, cleanup)
	if rc:
		return

	os.system('eject "%s"' %cdrom)

if __name__ == "__main__":
	parse_cmdline(sys.argv[1:])

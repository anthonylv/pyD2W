===== pyD2W =====
A Drupal to WordPress database migration tool using Python
by Another Cup of Coffee Limited

This is our in-house tool for performing the bulk of the migration from
Drupal 6 to WordPress 3.5. It requires an SQL script file. A sample is included
but you will need to edit it to match your own migration requirements. (See below.)

If you're not sure how to make the appropriate changes, Another Cup of Coffee Limited
will be happy to do the work. Contact us at http://anothercoffee.net


--- Installation and use ---
(1) You will need to install the following Python modules:
* MySQLdb for accessing MySQL databases
* prettytable for displaying results in a table format
* phpserialize for unserializing Drupal fields

(2) Edit the included sql sample files in the sql-sample directory to
suit your migration requirements. At a minimum, you will need the migration
script itself (see the sample migration_standard. sql file).

For more information on the migration file, see:
http://anothercoffee.net/drupal-to-wordpress-migration-explained/

Useful supporting script files are a dump of a pre-configured (but empty) WordPress
installation and a dump of your Drupal database in a clean state before any migration
attempts. Since migrations can often take several passes of fine-tuning, it can help
to reset your databases.

(3) Run the utility using the help flag to view the available commands:
python d2w.py -h


--- CAUTION ---
Make a backup of both your Drupal and WordPress databases before running this
tool. USE IS ENTIRELY AT YOUR OWN RISK.

First released 2015-02-03 by Anthony Lopez-Vito of Another Cup of Coffee Limited
http://anothercoffee.net

All code is released under The MIT License.
Please see LICENSE.txt.


--- Credits ---
* Scott Anderson of Room 34 Creative Services.
  The queries for migrating from Drupal to WordPress are based on a post
  by Room 34 in http://blog.room34.com/archives/4530

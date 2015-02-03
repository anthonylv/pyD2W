/*******************************************************************************
 * Drupal to WordPress database migration tool
 * by Another Cup of Coffee Limited
 *
 * Version 0.2
 *
 * This script is based on the Drupal to WordPress Migration tool
 * drupaltowordpress-d6w35 version 3 by Another Cup of Coffee Limited.
 * It allows you to run a Drupal to WordPress migration without the user interface.
 *
 * This was a custom script written for the specific needs of a client but may be
 * useful for other migrations. I've stripped out any identifying information but
 * left some generic data to provide an example.
 *
 * Migration options are set directly in this script.
 *
 * 
 * CAUTION:
 * Make a backup of both your Drupal and WordPress databases before running this
 * tool. USE IS ENTIRELY AT YOUR OWN RISK.
 * 
 * First released by Anthony Lopez-Vito of Another Cup of Coffee Limited
 * http://anothercoffee.net
 * 
 * All code is released under The MIT License.
 * Please see LICENSE.txt.
 *
 * Credits: Please see README.txt for credits 
 *
 *******************************************************************************/


/********************
 * Clear out WP tables and working tables..
 */
TRUNCATE TABLE acc_wp_comments;
TRUNCATE TABLE acc_wp_links;
TRUNCATE TABLE acc_wp_postmeta;
TRUNCATE TABLE acc_wp_posts;
TRUNCATE TABLE acc_wp_term_relationships;
TRUNCATE TABLE acc_wp_term_taxonomy;
TRUNCATE TABLE acc_wp_terms;
TRUNCATE TABLE acc_wp_users;
DROP TABLE IF EXISTS acc_duplicates;
DROP TABLE IF EXISTS acc_news_terms;
DROP TABLE IF EXISTS acc_tags_terms;
DROP TABLE IF EXISTS acc_wp_tags;
DROP TABLE IF EXISTS acc_users_post_count;
DROP TABLE IF EXISTS acc_users_comment_count;
DROP TABLE IF EXISTS acc_users_with_content;
DROP TABLE IF EXISTS acc_users_post_count;
DROP TABLE IF EXISTS acc_wp_categories;
DROP TABLE IF EXISTS acc_users_with_comments;
/*
 * For some installations, we make changes to the wp_usermeta table
TRUNCATE TABLE acc_wp_usermeta;
*/



/********************
 * Create a table of tags.
 *
 * Exclude terms from vocabularies that we might later
 * convert into categories. See stage below where we create categories 
 * and sub-categories.
 */
CREATE TABLE acc_wp_tags AS
	SELECT 
		tid,
		vid,
		name 
	FROM term_data;

	
/********************
 * Create the tags in the WordPress database
 */
 
/* Add the tags to WordPress.
 *
 * A clean WordPress database will have term_id=1 for Uncategorized.
 * Use REPLACE as this may conflict with a Drupal tid
 */

/* ASSUMPTION:
 * Assuming that this point the Drupal term_data table
 * has been cleaned of any duplicate names as any
 * duplicates will be lost.
 */
REPLACE INTO acc_wp_terms (term_id, name, slug, term_group) 
	SELECT 
		d.tid,
		d.name,
		REPLACE(LOWER(d.name), ' ', '_'),
		d.vid 
	FROM term_data d WHERE d.tid IN (
		SELECT t.tid FROM acc_wp_tags t
		);

/* Convert these Drupal terms into tags */
REPLACE INTO acc_wp_term_taxonomy (
		term_taxonomy_id,
		term_id,
		taxonomy,
		description,
		parent)
	SELECT DISTINCT 
		d.tid,
		d.tid 'term_id',
		'post_tag', /* This string makes them WordPress tags */
		d.description 'description',
		0 /* In this case, we don't give tags a parent */ 
	FROM term_data d
	WHERE d.tid IN (SELECT t.tid FROM acc_wp_tags t);


/********************
 * Create the categories and sub-categories in the WordPress database.
 */
/* Add terms associated with a Drupal vocabulary into WordPress.
 *
 */

CREATE TABLE acc_wp_categories AS
	SELECT 
		tid,
		vid,
		name 
	FROM term_data;
	
	
REPLACE INTO acc_wp_terms (term_id, name, slug, term_group) 
	SELECT DISTINCT 
		d.tid,
		d.name,
		REPLACE(LOWER(d.name), ' ', '_'),
		d.vid 
	FROM term_data d WHERE d.tid IN (
			SELECT t.tid FROM acc_wp_categories t
			);
	
/* Convert these Drupal terms into sub-categories by setting parent */
REPLACE INTO acc_wp_term_taxonomy (
		term_taxonomy_id,
		term_id,
		taxonomy,
		description,
		parent)
	SELECT DISTINCT 
		d.tid,
		d.tid 'term_id',
		'category',
		d.description 'description',
		0 /* In this case, we don't give tags a parent */
	FROM term_data d
	WHERE d.tid IN (SELECT t.tid FROM acc_wp_categories t);
	

/********************
 * Re-insert the Uncategorized term replaced previously.
 *
 * We may have replaced or deleted the Uncategorized category
 * during an earlier query. Re-insert it if you want an 
 * Uncategorized category.
 */
INSERT INTO acc_wp_terms (name, slug, term_group)
	VALUES ('Uncategorized', 'uncategorized', 0);
INSERT INTO acc_wp_term_taxonomy (		
		term_taxonomy_id,
		term_id,
		taxonomy,
		description,
		parent,
		count)
	SELECT DISTINCT 
		t.term_id,
		t.term_id,
		'category',
		t.name,
		0,
		0
	FROM acc_wp_terms t
	WHERE t.slug='uncategorized';
	

/********************
 * Create WP Posts from Drupal nodes
 */
REPLACE INTO acc_wp_posts (
		id,
		post_author,
		post_date,
		post_content,
		post_title,
		post_excerpt,
		post_name,
		post_modified,
		post_type,
		post_status,
		to_ping,
		pinged,
		post_content_filtered) 
	SELECT DISTINCT
		n.nid 'id',
		n.uid 'post_author',
		DATE_ADD(FROM_UNIXTIME(0), interval n.created second) 'post_date',
		r.body 'post_content',
		n.title 'post_title',
		r.teaser 'post_excerpt',
		IF(a.dst IS NULL,n.nid, SUBSTRING_INDEX(a.dst, '/', -1)) 'post_name',
		DATE_ADD(FROM_UNIXTIME(0), interval n.changed second) 'post_modified',
		n.type 'post_type',
		IF(n.status = 1, 'publish', 'private') 'post_status',
		' ',
		' ',
		' '
	FROM node n
	INNER JOIN node_revisions r USING(vid)
	LEFT OUTER JOIN url_alias a
		ON a.src = CONCAT('node/', n.nid)
		WHERE n.type IN (
            'page',
            'story');


/*
 * Combine field teaser and links content into body
 */
DROP TABLE IF EXISTS acc_wp_ct_links;
CREATE TABLE acc_wp_ct_links AS
	SELECT DISTINCT
		n.nid 'nid',
		n.vid 'vid',
		n.uid 'post_author',
		DATE_ADD(FROM_UNIXTIME(0), interval n.created second) 'post_date',
        CONCAT(r.body, CONCAT(f.field_teaser_value,p.field_press_link_url)) 'post_content',
        f.field_teaser_value 'field_teaser_value',
        p.field_press_link_url 'field_press_link_url',
		n.title 'post_title',
		r.teaser 'post_excerpt',
		DATE_ADD(FROM_UNIXTIME(0), interval n.changed second) 'post_modified',
		n.type 'post_type',
		IF(n.status = 1, 'publish', 'private') 'post_status'
	FROM node n
	INNER JOIN content_field_teaser f USING(vid)
	INNER JOIN content_type_press p USING(vid)		
	INNER JOIN node_revisions r USING(vid)
        WHERE n.type IN (
            'page',
            'story');

UPDATE acc_wp_posts p
INNER JOIN acc_wp_ct_links l ON
    p.id=l.vid
SET 
    p.post_content = l.post_content;
WHERE p.type IN (
        'page',
        'story');
            

/* Set the content types that should be converted into 'posts' */
UPDATE acc_wp_posts SET post_type = 'post' 
	WHERE post_type IN (
        'page',
        'story');
		
		
/* The rest of the content types are converted into pages */
UPDATE acc_wp_posts SET post_type = 'page' WHERE post_type NOT IN ('post');

/********************
 * Housekeeping queries for terms
 */

/* Associate posts with terms */
INSERT INTO acc_wp_term_relationships (
	object_id,
	term_taxonomy_id) 
	SELECT DISTINCT nid, tid FROM term_node;
 
/* Update tag counts */
UPDATE acc_wp_term_taxonomy tt 
	SET count = ( SELECT COUNT(tr.object_id)
	FROM acc_wp_term_relationships tr
	WHERE tr.term_taxonomy_id = tt.term_taxonomy_id);

/* Fix taxonomy
 * Found in room34.com queries: Fix taxonomy
 * http://www.mikesmullin.com/development/migrate-convert-import-drupal-5-to-wordpress-27/#comment-27140
 *
 * IS THIS NECESSARY?

UPDATE IGNORE acc_wp_term_relationships, acc_wp_term_taxonomy
	SET acc_wp_term_relationships.term_taxonomy_id = acc_wp_term_taxonomy.term_taxonomy_id
	WHERE acc_wp_term_relationships.term_taxonomy_id = acc_wp_term_taxonomy.term_id;
*/

/* Set default category.
 *
 * Manually look in the database for the term_id of the category you want to set as
 * the default category.
 */
UPDATE acc_wp_options SET option_value='159' WHERE option_name='default_category';
UPDATE acc_wp_term_taxonomy SET taxonomy='category' WHERE term_id=159;/* Unclassified term */


/********************
 * Migrate comments
 */
REPLACE INTO acc_wp_comments (
	comment_ID,
	comment_post_ID,
	comment_date,
	comment_content,
	comment_parent,
	comment_author,
	comment_author_email,
	comment_author_url,
	comment_approved)
	SELECT DISTINCT 
		cid,
		nid,
		FROM_UNIXTIME(timestamp),
		comment,
		pid,
		name,
		mail,
		SUBSTRING(homepage,1,200),
		((status + 1) % 2) FROM comments;

/* Update comment counts */
UPDATE acc_wp_posts
	SET comment_count = ( SELECT COUNT(comment_post_id) 
	FROM acc_wp_comments
	WHERE acc_wp_posts.id = acc_wp_comments.comment_post_id);

/********************
 * Migrate Drupal Authors into WordPress
 *
 * In this case we are migrating only users who have created a post.
 */
 
/*
 * See additional queries for migrating authors:
 * migrate-authors.sql
 */

/* Delete all WP Authors except for admin */
DELETE FROM acc_wp_users WHERE ID > 1;
DELETE FROM acc_wp_usermeta WHERE user_id > 1;

/* Set Drupal's admin password to a known value.
 *
 * This avoids hassles with trying to reset the password on 
 * the new WordPress installation.
 */
UPDATE users set pass=md5('password') where uid = 1;
 
/* Create table of users who have created a post */
CREATE TABLE acc_users_post_count AS
SELECT
	u.uid,
	u.name,
	u.mail,
	count(n.uid) node_count
FROM node n
INNER JOIN users u on n.uid = u.uid
/*
WHERE n.type IN (
	 List the post types we migrated earlier
    'page',
    'story')
*/	
GROUP BY u.uid
ORDER BY node_count;

/* Add authors using table of users who have created a post */
INSERT IGNORE INTO acc_wp_users (
	ID,
	user_login,
	user_pass,
	user_nicename,
	user_email,
	user_registered,
	user_activation_key,
	user_status,
	display_name) 
	SELECT DISTINCT
		u.uid,
		REPLACE(LOWER(u.name), ' ', '_'),
		u.pass,
		u.name,
		u.mail,
		FROM_UNIXTIME(created),
		'', 
		0,
		u.name
	FROM users u
	WHERE u.uid IN (SELECT uid FROM acc_users_post_count);

/* Sets all authors to "author" by default; next section can selectively promote individual authors */
INSERT IGNORE INTO acc_wp_usermeta (
	user_id,
	meta_key,
	meta_value)
	SELECT DISTINCT 
		u.uid,
		'wp_capabilities',
		'a:1:{s:6:"author";s:1:"1";}'
	FROM users u
	WHERE u.uid IN (SELECT uid FROM acc_users_post_count);	

INSERT IGNORE INTO acc_wp_usermeta (
	user_id,
	meta_key,
	meta_value)
	SELECT DISTINCT
		u.uid,
		'wp_user_level',
		'2'
	FROM users u
	WHERE u.uid IN (SELECT uid FROM acc_users_post_count);
	
/* Reassign post authorship to admin for posts have no author */
UPDATE acc_wp_posts 
	SET post_author = 1 
	WHERE post_author NOT IN (SELECT DISTINCT ID FROM acc_wp_users);


/********************
 * Housekeeping for WordPress options
 */

/* Update filepath */
UPDATE acc_wp_posts SET post_content = REPLACE(post_content, '"/files/', '"/wp-content/uploads/');

/* Set site name */
UPDATE acc_wp_options SET option_value = ( SELECT value FROM variable WHERE name='site_name') WHERE option_name = 'DrupalToWordPress';

/* Set site description */
UPDATE acc_wp_options SET option_value = ( SELECT value FROM variable WHERE name='site_slogan') WHERE option_name = 'Drupal to WordPress migration';

/* Set site email */
UPDATE acc_wp_options SET option_value = ( SELECT value FROM variable WHERE name='site_mail') WHERE option_name = 'support@needthebuzz.com';

/* Set permalink structure */
UPDATE acc_wp_options SET option_value = '/%postname%/' WHERE option_name = 'permalink_structure';



/********************
 * Create URL redirects table
 *
 * This table will not be used for the migration but may be useful if
 * you need to manually create redirects from Drupal aliases
 */
/*
DROP TABLE IF EXISTS acc_redirects;
CREATE TABLE acc_redirects AS
	SELECT
		CONCAT('dietdetective_d6/', 
			IF(a.dst IS NULL,
				CONCAT('node/', n.nid), 
				a.dst
			)
		) 'old_url',
		IF(a.dst IS NULL,n.nid, SUBSTRING_INDEX(a.dst, '/', -1)) 'new_url',
		'301' redirect_code
	FROM node n
	INNER JOIN node_revisions r USING(vid)
	LEFT OUTER JOIN url_alias a
		ON a.src = CONCAT('node/', n.nid);
*/	
			
			
/********************
* Run additional query to import users who have commented
* but haven't created any of the selected content types 
*
* Running this will throw errors if you haven't manually
* copied over required tables and renamed copies 
* to the tables names below.
*
* Tables requred for these queries:
* 	acc_users_with_comments: empty copy of wp_users
* 	acc_users_add_commenters: empty copy of wp_users
* 	acc_wp_users: copy of wp_users from wordpress database containing users
*
*/

CREATE TABLE acc_users_with_comments LIKE acc_wp_users;
CREATE TABLE acc_users_add_commenters LIKE acc_wp_users;
CREATE TABLE acc_wp_users LIKE acc_wp_users;
INSERT INTO acc_wp_users SELECT * FROM acc_wp_users;

/* Create table of users who have created a comment */
CREATE TABLE acc_users_comment_count AS
SELECT
	u.uid,
	u.name,
	count(c.uid) comment_count
FROM comments c
INNER JOIN users u on c.uid = u.uid
GROUP BY u.uid;

INSERT IGNORE INTO acc_users_with_comments (
	ID,
	user_login,
	user_pass,
	user_nicename,
	user_email,
	user_registered,
	user_activation_key,
	user_status,
	display_name) 
	SELECT DISTINCT
		u.uid,
		REPLACE(LOWER(u.name), ' ', '_'),
		u.pass,
		u.name,
		u.mail,
		FROM_UNIXTIME(created),
		'', 
		0,
		u.name
	FROM users u
	WHERE u.uid IN (SELECT uid FROM acc_users_comment_count);

/* Build a table of users who have commented but 
 * not already added to WordPress' wp_users */
INSERT IGNORE INTO acc_users_add_commenters (
	ID,
	user_login,
	user_pass,
	user_nicename,
	user_email,
	user_registered,
	user_activation_key,
	user_status,
	display_name) 
	SELECT DISTINCT
		u.ID,
		u.user_login,
		u.user_pass,
		u.user_nicename,
		u.user_email,
		u.user_registered,
		'', 
		0,
		u.display_name
	FROM acc_users_with_comments u
	WHERE u.ID NOT IN (SELECT ID FROM acc_wp_users);
	
/* Combine the tables 
 * Remember to copy wp_users back into wordpress database
 */
INSERT IGNORE
  INTO acc_wp_users 
SELECT *
  FROM acc_users_add_commenters;	


/********************
 * Additional customisations
 *
 * --- ERROR: "You do not have sufficient permissions to access this page" ---
 *
 * If you receive this error after logging in to your new WordPress installation, it's possible that the 
 * database prefix on your new WordPress site is not set correctly. This may happen if, for example, you used
 * a local WordPress installation to run the migration before setting up on your live WordPress installation.
 *
 * Try running one of the queries below.
 *
 * Sources:
 * (1) http://wordpress.org/support/topic/you-do-not-have-sufficient-permissions-to-access-this-page-98
 * (2) http://stackoverflow.com/questions/13815461/you-do-not-have-sufficient-permissions-to-access-this-page-without-any-change
 *
 * OPTION 1
 * UPDATE wp_new_usermeta SET meta_key = REPLACE(meta_key,'oldprefix_','newprefix_');
 * UPDATE wp_new_options SET option_name = REPLACE(option_name,'oldprefix_','newprefix_');
 *
 * OPTION 2
 * update wp_new_usermeta set meta_key = 'newprefix_usermeta' where meta_key = 'wp_capabilities';
 * update wp_new_usermeta set meta_key = 'newprefix_user_level' where meta_key = 'wp_user_level';
 * update wp_new_usermeta set meta_key = 'newprefix_autosave_draft_ids' where meta_key = 'wp_autosave_draft_ids';
 * update wp_new_options set option_name = 'newprefix_user_roles' where option_name = 'wp_user_roles';
 *
 * 
 * --- Incorrect domain in link URLs ---
 * 
 * WordPress stores the domains in the database. If you performed the migration on a local or development server,
 * there's a good chance that the links will be incorrect after migrating to your live server. Use the Interconnect IT
 * utility to run a search and replace on your database. This will also correct changed database prefixes.
 *
 * https://interconnectit.com/products/search-and-replace-for-wordpress-databases/
 *
 *
 * END
 *
 ********************/
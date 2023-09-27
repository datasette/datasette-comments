BEGIN;


INSERT INTO datasette_comments_threads VALUES
  ('01haxh0gtj2b4t426xp3b1a1ce','2023-09-22 04:05:19','1','row','my_data','students','["aaa"]',NULL,NULL);



INSERT INTO datasette_comments_comments
  (id, thread_id, created_at, updated_at, author_actor_id, contents, mentions, hashtags, past_revisions)
VALUES
  ('01haxh0gtk7sypf7j8cv83mmem','01haxh0gtj2b4t426xp3b1a1ce','2023-09-22 04:05:19','2023-09-22 04:05:19','1','lol thats funny #tag1','[]','["tag1"]','[]'),
  ('01haxh0s77g8y8fh7k1w08pwt1','01haxh0gtj2b4t426xp3b1a1ce','2023-09-22 04:05:28','2023-09-22 04:05:28','1','anotha one #tag2','[]','["tag2"]','[]');
/*
  ('01haxjrn9cf1nk7y4ftdfsae49','01haxjrn99fq1n4hxvka991zdg','2023-09-22 04:35:59','2023-09-22 04:35:59','2','a','[]','[]','[]'),
  ('01haxjrrhqj0q432cqmty71jq2','01haxjrn99fq1n4hxvka991zdg','2023-09-22 04:36:02','2023-09-22 04:36:02','2','b','[]','[]','[]'),
  ('01haxjrtz5hckbsx3faex3fx42','01haxjrn99fq1n4hxvka991zdg','2023-09-22 04:36:05','2023-09-22 04:36:05','2','c','[]','[]','[]'),
  ('01haxjrxhxz8cx3mfg9567zq8k','01haxjrn99fq1n4hxvka991zdg','2023-09-22 04:36:07','2023-09-22 04:36:07','2','#new','[]','["new"]','[]'),
  ('01hayx3j4rhh20eq2rhwy1kd9b','01hayx3j4q26f48w53ntdfzhd2','2023-09-22 16:55:56','2023-09-22 16:55:56','1','lol #wut','[]','["wut"]','[]'),
  ('01hb799gwk479ccgf5dsxkvxc2','01hb799gwfz1s7kqzsftgj3qxg','2023-09-25 23:02:50','2023-09-25 23:02:50','1','the OG','[]','[]','[]'),
  ('01hb79mdyqjyppm1m3rcexjcky','01hb79mdypcv7smv4c5jjbv7pd','2023-09-25 23:08:47','2023-09-25 23:08:47','1','burr sir','[]','[]','[]'),
  ('01hb79n6b276npsv34ea6va2h2','01hb79n6b11x8pvtvw7fvy28yb','2023-09-25 23:09:12','2023-09-25 23:09:12','1','who is this guy','[]','[]','[]'),
  ('01hb7axwsnbxeb0cyerznmhcpe','01hb79n6b11x8pvtvw7fvy28yb','2023-09-25 23:31:26','2023-09-25 23:31:26','1','#sus','[]','["sus"]','[]'),
  ('01hb7fpzjp87dbrbewayzwkhx8','01hb7fpzj1ra7ymy3ns5nx4mkm','2023-09-26 00:55:02','2023-09-26 00:55:02','1','asdfasdfsadf?','[]','[]','[]'),
  ('01hb7skhhcazydr4f7ej0z3ps0','01hb7skhh99g5fkxmsn2bye7z0','2023-09-26 03:47:56','2023-09-26 03:47:56','1','asdf','[]','[]','[]'),
  ('01hb7sm87dv8vg7m2drndy8gxb','01hb7sm87cv8zhvq9ha1q6g8zk','2023-09-26 03:48:19','2023-09-26 03:48:19','1',replace('yo\n','\n',char(10)),'[]','[]','[]'),
  ('01hb7smex6v9wysvwjng6vdmmj','01hb7smex5haw4s5j4wkx7m90x','2023-09-26 03:48:26','2023-09-26 03:48:26','1','anotha one','[]','[]','[]'),
  ('01hb7snzq7835b656ajwhpm9p4','01hb7snzq6v9q2p8xts8j883cs','2023-09-26 03:49:16','2023-09-26 03:49:16','1','asdf','[]','[]','[]'),
  ('01hb7sq84tytd00wye2krbtn4w','01hb7sq84r7xdb8a14f2nx97ar','2023-09-26 03:49:57','2023-09-26 03:49:57','1','fff','[]','[]','[]'),
  ('','01hb7ssnq3fbseymbmw5nhsaet','2023-09-26 03:51:16','2023-09-26 03:51:16','1','ccc','[]','[]','[]'),
  ('','01hb95fk36aszmx5ee82p6vn9t','2023-09-26 16:34:43','2023-09-26 16:34:43','1','vxcvcxv','[]','[]','[]'),
  ('01hb95fst5hze0n8md6vg2e6eq','01hb95fk36aszmx5ee82p6vn9t','2023-09-26 16:34:50','2023-09-26 16:34:50','1','#sus','[]','["sus"]','[]'),
  ('01hb95kjm0d7w0yzn8tr6v7xzv','01haxjrn99fq1n4hxvka991zdg','2023-09-26 16:36:54','2023-09-26 16:36:54','1','@simonw','["simonw"]','[]','[]');
  */

INSERT INTO datasette_comments_reactions(id, comment_id, reactor_actor_id, reaction)
VALUES
  ('01haxhkaa5ew1k09bp3s2emmwy','01haxh0gtk7sypf7j8cv83mmem','1','❤️'),
  ('01hb7ssnq58s19xk3vzqtt75g6','01haxh0gtk7sypf7j8cv83mmem','2','❤️'),
  ('01hb95fk3ea93yzket82qqwj0g','01haxh0s77g8y8fh7k1w08pwt1','1','🚀');
  --  👍 😀
COMMIT;

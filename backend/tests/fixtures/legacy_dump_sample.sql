--
-- PostgreSQL database dump
--
SET statement_timeout = 0;
CREATE TYPE public.user_type_enum AS ENUM ('student', 'teacher');
CREATE TABLE public.users (
    user_id bigint NOT NULL,
    username character varying(50) NOT NULL
);
ALTER TABLE public.users OWNER TO postgres;

COPY public.users (user_id, username, password_hash, real_name, user_type, account_status, register_time, created_at, is_deleted, legacy_flag) FROM stdin;
1	admin	hash1	管理员	student	active	2025-08-01 12:34:56.789+00	2025-08-01 12:34:56.789+00	f	t
2	张三	hash2	张三	teacher	active	2025-08-02 08:00:00+08	2025-08-02 00:00:00+00	f	f
3	tab\tname	hash3	反斜杠\\名字	student	active	\N	2025-08-03 00:00:00+00	f	f
\.

COPY public.system_configs (id, config_key, config_value, is_encrypted, description) FROM stdin;
1	site_name	EasyInvoiceMgr	f	站点名称
2	smtp_password	ciphertext	t	\N
\.

COPY public.ignored_table (id) FROM stdin;
99
\.

SELECT pg_catalog.setval('public.users_user_id_seq', 3, true);

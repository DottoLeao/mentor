create extension if not exists vector;

create table if not exists chunks (
    id bigserial primary key,
    source text not null,
    url text not null,
    title_path text not null,
    content text not null,
    version text not null,
    collected_at timestamptz not null,
    embedding vector(1024) not null,
    tsv tsvector generated always as (
        to_tsvector('simple', title_path || ' ' || content)
    ) stored,
    unique (source, url, title_path)
);

create index if not exists chunks_embedding_hnsw
    on chunks using hnsw (embedding vector_cosine_ops);
create index if not exists chunks_tsv_gin on chunks using gin (tsv);
create index if not exists chunks_source on chunks (source);

create table if not exists usage (
    install_id text not null,
    day date not null,
    count int not null default 0,
    primary key (install_id, day)
);

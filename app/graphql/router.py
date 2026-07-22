import strawberry
from strawberry.fastapi import GraphQLRouter
from app.graphql.queries import Query
from app.graphql.mutations import Mutation
from app.graphql.context import get_graphql_context

schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_graphql_context
)

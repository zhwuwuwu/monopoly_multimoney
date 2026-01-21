# 开发笔记

## TODO
1. rednote 平台接入
2. mcp tool 注册
3. 更换 llm api
4. 调整 生成文章prompt
5. 调整 agent 人设
6. 审核拆成独立agent/mcp


columnist_syncronizer agent
   - writer
     - load material
     - online research
     - writing
   - reviewer
   - publish tool


在rnotegen目录下，我想从零开始实现一个专栏作家agent，请使用openaisdk作为agent框架并通过mcp协议来调用外部工具，请预留出配置system prompt的接口，包括一个配置文件可以设置作家的角色和立场，一个配置文件可以设置专栏的题目和主题。此agent应该可以根据配置文件的角色和专栏的主题生成内容，我会提供一些基础的素材，此agent应该基于此素材生成能够阐述自己的立场的文章。素材可能包括新闻，历史，理论等等。在攥写文章的时候该agent必须基于事实，它可以通过调用mcp工具查阅互联网知识。文章目前准备发表在小红书平台，请你通过mcp工具调用对应接口提供信息获取和发表功能。


i want to refactor the structure of the current, hope to organize the whole process with a hardcoded syncronizer as main function. Then we use a writer agent to load material, do the online research, and write the article, another reviewer agent can check the generated article from the writer agent and the task will return to the writer if the review score is low. Finally, the syncronizer request to publish the content to the rednote platform depends on the user's setting.
For the writer and reviewer agent, you need to use OpenAI Agent SDK. For the tools, you should gather all the functions in a mcp server using SSE protocol.
Do the planning first.
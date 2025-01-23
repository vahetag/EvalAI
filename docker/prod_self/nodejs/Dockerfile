# #########################################################################################
FROM node:14.20.0

WORKDIR /code
ARG NODE_ENV

# 1. Copy build scripts
COPY package.json bower.json gulpfile.js .eslintrc karma.conf.js /code/

# 2. Install dependencies
RUN npm install -g bower gulp gulp-cli && \
    npm install phantomjs-prebuilt && \
    npm link gulp && \
    npm cache clean -f && \
    npm install && \
    npm install -g qs && \
    bower install --allow-root

# 3. Copy the actual source
COPY frontend /code/frontend
# RUN touch frontend/index.html
# CMD ["touch", "frontend/index.html"]

# 4. Build
# If you want to bake it in at image build time:
# RUN gulp production
CMD "gulp" $NODE_ENV
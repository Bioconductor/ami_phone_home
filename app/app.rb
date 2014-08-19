require 'sinatra'
require 'pp'

get '/' do
  'Hello world!'
end


post '/phone-home' do
    pp params
    puts request.ip
    puts "real IP is #{@env['HTTP_X_REAL_IP']}"
#    require 'pry';binding.pry
    "thanx\n"
end
#!/usr/bin/ruby

# JIRA query script
# -----------------
# * Queries data from JIRA REST API.
# * Usage requires valid JIRA credentials with access rights to the target project.
# * Instead of JIRA username/password you can also provide an authorization token, that is a base64-encoded string of "<username>:<password>"
#
# https://developer.atlassian.com/server/jira/platform/rest-apis/
# https://docs.atlassian.com/software/jira/docs/api/REST/latest/

require 'base64'
require 'cgi'
require 'json'
require 'net/http'
require 'net/https'

class JiraQuery

	def initialize(api_url, user, password, auth_token, project, version, logger=nil)
		@api_url = api_url
		@project = project
		@version = version
		@auth_token = nil
		@logger = logger
		
		if user != nil and password != nil
			@auth_token = Base64.encode64("#{user}:#{password}").strip!
		else
			if auth_token != nil
				@auth_token = auth_token
			else
				raise "No user/password or auth token given"
			end
		end
	end
	
	def query(path)
		begin
			uri = URI.parse("#{@api_url}#{path}")
			response = Net::HTTP.start(uri.host, uri.port, :use_ssl => true, :verify_mode => OpenSSL::SSL::VERIFY_NONE) do |https|
				request = Net::HTTP::Get.new(uri.request_uri)
				request["Authorization"] = "Basic " + @auth_token
				https.request(request)
			end
			if response.message != "OK"
				raise "HTTP error: " + response.message
			end
			return response.body
		rescue Exception => e
			error_message = "JIRA query failed: " + e.message + "\n" + e.backtrace.join('\n')
			if @logger != nil
				@logger.error(error_message)
			end
			raise error_message.gsub('\n', '<br>')
		end
		return nil
	end
	
	def search(search_str, max_results=nil)
		return JSON.parse(query("/search?jql=" + CGI.escape(search_str) + ((max_results != nil) ? "&maxResults=" + max_results.to_s : "")))
	end
	
	def check_project()
		begin
			query("/project/#{@project}")
		rescue
			raise "Project '#{@project}' not found or given user has no access to it"
		end
	end
	
	def get_versions()
		return JSON.parse(query("/project/#{@project}/versions"))
	end
	
	def get_version(name)
		versions = get_versions()
		versions.each { |version|
			if version["name"] == name
				return version
			end
		}
		return nil
	end
	
	def get_issue_count(status, type=nil, priority=nil)	
		search_str = "project = #{@project} AND fixVersion = #{@version} AND status #{status}#{(type != nil) ? " AND issuetype = " + type : ""}#{(priority != nil) ? " AND priority = " + priority : ""}"
		return search(search_str, 0)["total"]
	end
	
	def get_issues(type)
		if type == "open_all"
			return get_issue_count("!= Closed", nil, nil)
		elsif type == "resolved_all"
			return get_issue_count("= Resolved", nil, nil)
		else
			return get_issue_count("!= Closed", type, nil)
		end
	end
	
	def get_issue_priorities()
		priorities = {}
		for priority in ["Blocker","High","Medium","Low"]
			search_str = "project = #{@project} AND fixVersion = #{@version} AND status != Closed AND priority = #{priority}"
			priorities[priority] = search(search_str, 0)["total"]
		end
		return priorities
	end
end
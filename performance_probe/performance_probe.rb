#!/usr/bin/ruby

# Performance measurement probe
# -----------------------------
# * Collects process performance metrics data while tests are being executed.
# * Requires PowerShell to be available on the system

require 'logger'
require 'optparse'
require 'json'

class PerformanceProbe
	def initialize(options)
		@process = options[:process]
		@interval_seconds = options[:interval_seconds]
		@output_dir = options[:output_dir]
		
		@log = Logger.new(File.join(@output_dir, "performance_probe.log"))
		@log.level = Logger::DEBUG
		
		@exec_threads = []
		@measurements = {:duration => 0,
						 :cpu => [], 
						 :mem_workingset => [], 
						 :mem_commitsize => [],
						 :threads => [],
						 :handles => [],
						 :io_read_bytes => [],
						 :io_write_bytes => []}
	end

	def run_shell_command(cmd)
		retvalue = %x[#{cmd}]
		retcode = $?.exitstatus
		return (retcode == 0), retvalue
	end
	
	def run_powershell_command(cmd)
		result, value = run_shell_command("powershell -command \"& {#{cmd}}\"")
		return result, value
	end
	
	def is_process_running(name)
		_, value = run_shell_command("tasklist")
		if value.include?(name)
			return true
		else
			return false
		end
	end
	
	def measure(metric, counter)
		Thread.current[:stop] = false
		while not Thread.current[:stop]
			begin
				if is_process_running(@process)
					cmd = '(Get-Counter -Counter \"\Process(' + @process + ')\\' + counter + '\").CounterSamples[0].CookedValue;'
					result, value = run_powershell_command(cmd)
					if result
						@measurements[metric].push({:timestamp => (Time.now.to_f * 1000).to_i, 
													:value => Float(value.strip.gsub(",",".")).round(2)})
					else
						@log.error("Failed to get measurement: #{value}")
					end
				end
			rescue Exception => e
				@log.error("Failed to get measurement: #{e.message}")
			end
			sleep(@interval_seconds)
		end
	end
	
	def stop()
		@exec_threads.each { |thread| 
			thread[:stop] = true
			thread.join() 
		}
	end
	
	def start()
		@exec_threads.push(Thread.new{ measure(:cpu, "% Processor Time") })
		@exec_threads.push(Thread.new{ measure(:mem_workingset, "Working Set - Private") })
		@exec_threads.push(Thread.new{ measure(:mem_commitsize, "Private Bytes") })
		@exec_threads.push(Thread.new{ measure(:threads, "Thread count") })
		@exec_threads.push(Thread.new{ measure(:handles, "Handle count") })
		@exec_threads.push(Thread.new{ measure(:io_read_bytes, "IO Read Bytes/sec") })
		@exec_threads.push(Thread.new{ measure(:io_write_bytes, "IO Write Bytes/sec") })
	end
	
	def get_results()
		return @measurements
	end
	
	def save_results(format="json")
		if format == "json"
			File.open(File.join(@output_dir, "metrics.json"), 'w') do |f|
				f.puts JSON.pretty_generate(@measurements)
			end
		elsif format == "csv"
			File.open(File.join(@output_dir, "metrics.csv"), 'w') do |f|
				f.puts "metric,timestamp,value"
				@measurements.each { |metric,results| 
					results.each { |result|
						f.puts metric.to_s + "," + result[:timestamp].to_s + "," + result[:value].to_s
					}
				}
			end
		end
	end
end

if __FILE__ == $0
	options = {}
	OptionParser.new do |opt|
	  opt.on('--process PROCESS') { |o| options[:process] = o }
	  opt.on('--interval_seconds INTERVAL_SECONDS') { |o| options[:interval_seconds] = Integer(o) }
	  opt.on('--output_dir OUTPUT_DIR') { |o| options[:output_dir] = o }
	end.parse!
	
	probe = PerformanceProbe.new(options)
	trap("INT") {
		probe.stop()
		probe.save_results()
	}
	probe.start()
end
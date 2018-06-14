addpath('[SPM_INSTALL]')

out_s = struct();
out_s.param    = '[OUTPUT_FILE_NAME]';
out_s.transf_w = '[TEMP_FILE_1]';
out_s.transf_v = '[TEMP_FILE_2]';

spm_brick_realign('[DATASET]', out_s)
